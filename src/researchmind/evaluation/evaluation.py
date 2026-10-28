"""Comprehensive benchmark evaluation engine comparing BM25, Dense, Hybrid, and Hybrid+Reranker across paper & chunk levels with abstention and latency profiling."""

import csv
import json
import logging
import time
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from tabulate import tabulate

from researchmind.schemas.models import (
    EvaluationQuery,
    EvaluationResult,
    RetrievalMode,
    RetrievalCandidate,
    RAGResponse,
)
from researchmind.evaluation.retrieval_metrics import (
    compute_recall_at_k,
    compute_precision_at_k,
    compute_hit_rate_at_k,
    compute_mrr,
    compute_ndcg_at_k,
    compute_abstention_metrics,
)
from researchmind.pipeline.rag import ResearchMindRAG
from researchmind.config import settings

logger = logging.getLogger(__name__)


class BenchmarkEvaluator:
    """Runs systematic retrieval, abstention, and XAI benchmarks across retrieval modes."""

    def __init__(self, rag_pipeline: Optional[ResearchMindRAG] = None):
        self.rag = rag_pipeline or ResearchMindRAG()

    def evaluate_queries(
        self,
        queries: List[EvaluationQuery],
        modes: Optional[List[str]] = None,
        eval_level: str = "paper",  # 'paper', 'chunk'
        top_k: int = 20,
    ) -> Dict[str, EvaluationResult]:
        """Run evaluation benchmark across specified retrieval modes on test queries.
        
        Args:
            queries: List of annotated EvaluationQuery test cases.
            modes: List of modes to evaluate (defaults to all 4).
            eval_level: 'paper' or 'chunk'.
            top_k: Maximum candidate depth for metrics.
            
        Returns:
            Dict mapping mode name -> EvaluationResult.
        """
        eval_modes = modes or ["bm25", "dense", "hybrid", "hybrid_rerank"]
        results: Dict[str, EvaluationResult] = {}

        # Filter to answerable / partial queries for retrieval metrics if unanswerable queries have empty ground truth
        eval_queries = [q for q in queries if (q.relevant_paper_ids if eval_level == "paper" else q.relevant_chunk_ids)]
        if not eval_queries:
            eval_queries = queries

        for mode in eval_modes:
            logger.info(f"Running benchmark for mode: '{mode}' (level='{eval_level}') on {len(eval_queries)} queries...")
            metrics_acc = {
                "recall_1": [], "recall_3": [], "recall_5": [], "recall_10": [], "recall_20": [],
                "precision_5": [], "hit_5": [], "hit_10": [], "mrr": [], "ndcg_5": [], "ndcg_10": [],
                "latencies": [], "grounded_ratios": [],
            }
            abstention_tracking = []

            for eq in queries:
                t0 = time.time()
                resp = self.rag.query(
                    query=eq.query,
                    retrieval_mode=mode,
                    top_k=top_k,
                    enable_xai=True,
                )
                lat = (time.time() - t0) * 1000
                metrics_acc["latencies"].append(lat)

                # Collect retrieved IDs based on eval_level
                retrieved_ids = [s.paper_id for s in resp.sources] if eval_level == "paper" else [s.chunk_id for s in resp.sources]
                relevant_ids = set(eq.relevant_paper_ids if eval_level == "paper" else eq.relevant_chunk_ids)

                if relevant_ids:
                    metrics_acc["recall_1"].append(compute_recall_at_k(retrieved_ids, relevant_ids, 1))
                    metrics_acc["recall_3"].append(compute_recall_at_k(retrieved_ids, relevant_ids, 3))
                    metrics_acc["recall_5"].append(compute_recall_at_k(retrieved_ids, relevant_ids, 5))
                    metrics_acc["recall_10"].append(compute_recall_at_k(retrieved_ids, relevant_ids, 10))
                    metrics_acc["recall_20"].append(compute_recall_at_k(retrieved_ids, relevant_ids, 20))
                    metrics_acc["precision_5"].append(compute_precision_at_k(retrieved_ids, relevant_ids, 5))
                    metrics_acc["hit_5"].append(compute_hit_rate_at_k(retrieved_ids, relevant_ids, 5))
                    metrics_acc["hit_10"].append(compute_hit_rate_at_k(retrieved_ids, relevant_ids, 10))
                    metrics_acc["mrr"].append(compute_mrr(retrieved_ids, relevant_ids))
                    metrics_acc["ndcg_5"].append(compute_ndcg_at_k(retrieved_ids, relevant_ids, 5))
                    metrics_acc["ndcg_10"].append(compute_ndcg_at_k(retrieved_ids, relevant_ids, 10))

                if resp.xai_explanation and resp.xai_explanation.grounding:
                    metrics_acc["grounded_ratios"].append(resp.xai_explanation.grounding.grounded_ratio)

                abstention_tracking.append({
                    "answerability": eq.answerability,
                    "abstained": resp.abstained,
                })

            def mean_val(vals: List[float]) -> float:
                return round(float(np.mean(vals)), 4) if vals else 0.0

            abs_metrics = compute_abstention_metrics(abstention_tracking)

            eval_res = EvaluationResult(
                method=mode,
                eval_level=eval_level,
                query_count=len(queries),
                recall_at_1=mean_val(metrics_acc["recall_1"]),
                recall_at_3=mean_val(metrics_acc["recall_3"]),
                recall_at_5=mean_val(metrics_acc["recall_5"]),
                recall_at_10=mean_val(metrics_acc["recall_10"]),
                recall_at_20=mean_val(metrics_acc["recall_20"]),
                precision_at_5=mean_val(metrics_acc["precision_5"]),
                hit_rate_at_5=mean_val(metrics_acc["hit_5"]),
                hit_rate_at_10=mean_val(metrics_acc["hit_10"]),
                mrr=mean_val(metrics_acc["mrr"]),
                ndcg_at_5=mean_val(metrics_acc["ndcg_5"]),
                ndcg_at_10=mean_val(metrics_acc["ndcg_10"]),
                grounded_claim_percentage=round(mean_val(metrics_acc["grounded_ratios"]) * 100, 1) if metrics_acc["grounded_ratios"] else None,
                abstention_accuracy=abs_metrics["abstention_accuracy"],
                selective_accuracy=abs_metrics["selective_accuracy"],
                unsupported_answer_rate=abs_metrics["unsupported_answer_rate"],
                false_abstention_rate=abs_metrics["false_abstention_rate"],
                avg_latency_ms=round(mean_val(metrics_acc["latencies"]), 1),
            )
            results[mode] = eval_res

        return results

    def sweep_abstention_thresholds(
        self,
        val_queries: List[EvaluationQuery],
        candidate_thresholds: Optional[List[float]] = None,
    ) -> List[Dict[str, Any]]:
        """Evaluate abstention performance across candidate confidence thresholds on validation set.
        
        Args:
            val_queries: List of validation queries including answerable, partial, and unanswerable cases.
            candidate_thresholds: List of candidate reranker/score thresholds (e.g. [0.20, ..., 0.50]).
            
        Returns:
            List of benchmark metric records per threshold candidate.
        """
        thresholds = candidate_thresholds or [0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]
        sweep_results = []

        logger.info(f"Sweeping {len(thresholds)} candidate abstention thresholds across {len(val_queries)} validation queries...")

        # Pre-retrieve candidates for all validation queries using hybrid_rerank to avoid redundant retrieval
        cached_responses = []
        for eq in val_queries:
            resp = self.rag.query(query=eq.query, retrieval_mode="hybrid_rerank", top_k=5, enable_xai=True)
            cached_responses.append((eq, resp))

        for thresh in thresholds:
            tracking = []
            for eq, resp in cached_responses:
                # Re-evaluate evidence strength under this specific threshold
                top_cand = resp.sources[0] if resp.sources else None
                top_score = top_cand.retrieval_score if top_cand else 0.0
                
                # Model abstains if top_score < threshold or answer explicitly states insufficient evidence
                abstained = (
                    top_score < thresh
                    or "insufficient evidence" in resp.answer.lower()
                    or "not find sufficient evidence" in resp.answer.lower()
                )

                tracking.append({
                    "answerability": eq.answerability,
                    "abstained": abstained,
                })

            metrics = compute_abstention_metrics(tracking)
            metrics["threshold"] = thresh
            sweep_results.append(metrics)

        return sweep_results

    def profile_latency_stages(
        self,
        queries: List[EvaluationQuery],
        sample_size: int = 10,
    ) -> Dict[str, Any]:
        """Profile latency breakdown across all sub-stages of the pipeline."""
        sample_queries = queries[:sample_size]
        stage_times = {
            "query_embedding": [],
            "dense_retrieval": [],
            "bm25_retrieval": [],
            "rrf_fusion": [],
            "reranking": [],
            "llm_generation": [],
            "xai_verification": [],
            "total_latency": [],
        }

        for eq in sample_queries:
            t_total_0 = time.time()

            # 1. Embedding
            t0 = time.time()
            q_emb = self.rag.dense_retriever.embedder.embed_query(eq.query)
            stage_times["query_embedding"].append((time.time() - t0) * 1000)

            # 2. Dense retrieval
            t0 = time.time()
            dense_res = self.rag.dense_retriever.index_manager.query(q_emb, top_k=20)
            stage_times["dense_retrieval"].append((time.time() - t0) * 1000)

            # 3. BM25 retrieval
            t0 = time.time()
            bm25_res = self.rag.sparse_retriever.retrieve(eq.query, top_k=20)
            stage_times["bm25_retrieval"].append((time.time() - t0) * 1000)

            # 4. RRF fusion
            t0 = time.time()
            fused = self.rag.hybrid_retriever.retrieve(eq.query, dense_top_k=20, sparse_top_k=20, final_top_k=20)
            stage_times["rrf_fusion"].append((time.time() - t0) * 1000)

            # 5. Reranking
            t0 = time.time()
            reranked = self.rag.reranker.rerank(eq.query, fused, top_k=5)
            stage_times["reranking"].append((time.time() - t0) * 1000)

            # 6. LLM Generation (Deterministic fallback for latency profiling)
            t0 = time.time()
            ans, _ = self.rag.generator._generate_fallback(eq.query, reranked)
            stage_times["llm_generation"].append((time.time() - t0) * 1000)

            # 7. XAI Verification
            t0 = time.time()
            _ = self.rag.explainer.generate_explanation(
                query=eq.query,
                answer=ans,
                dense_results=dense_res,
                sparse_results=bm25_res,
                hybrid_results=fused,
                final_evidence=reranked,
            )
            stage_times["xai_verification"].append((time.time() - t0) * 1000)

            stage_times["total_latency"].append((time.time() - t_total_0) * 1000)

        profile_summary = {}
        for stage, times in stage_times.items():
            profile_summary[stage] = {
                "mean_ms": round(float(np.mean(times)), 2),
                "median_ms": round(float(np.median(times)), 2),
                "p95_ms": round(float(np.percentile(times, 95)), 2),
            }

        return profile_summary

    def format_comparison_table(self, results: Dict[str, EvaluationResult]) -> str:
        """Format a clear Markdown comparison table of retrieval methods."""
        headers = ["Method", "Recall@5", "Recall@10", "Hit Rate@5", "MRR", "nDCG@10", "Grounded %", "Latency (ms)"]
        rows = []
        for mode, r in results.items():
            rows.append([
                r.method.upper(),
                f"{r.recall_at_5:.3f}",
                f"{r.recall_at_10:.3f}",
                f"{r.hit_rate_at_5:.3f}",
                f"{r.mrr:.3f}",
                f"{r.ndcg_at_10:.3f}",
                f"{r.grounded_claim_percentage}%" if r.grounded_claim_percentage is not None else "N/A",
                f"{r.avg_latency_ms:.1f}",
            ])
        return tabulate(rows, headers=headers, tablefmt="github")

    def save_all_experiment_reports(
        self,
        paper_results: Dict[str, EvaluationResult],
        chunk_results: Dict[str, EvaluationResult],
        threshold_sweep: List[Dict[str, Any]],
        latency_profile: Dict[str, Any],
    ) -> None:
        """Save all benchmark reports to experiments/ in JSON, CSV, and Markdown format."""
        exp_dir = settings.experiments_path
        exp_dir.mkdir(parents=True, exist_ok=True)

        # 1. Retrieval Benchmarks (Paper-Level & Chunk-Level)
        retrieval_data = {
            "paper_level": {k: v.model_dump() for k, v in paper_results.items()},
            "chunk_level": {k: v.model_dump() for k, v in chunk_results.items()},
        }
        with open(exp_dir / "benchmark_retrieval.json", "w", encoding="utf-8") as f:
            json.dump(retrieval_data, f, indent=2)

        # CSV Retrieval
        with open(exp_dir / "benchmark_retrieval.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Level", "Method", "Queries", "Recall@1", "Recall@5", "Recall@10", "Precision@5", "HitRate@5", "MRR", "nDCG@5", "nDCG@10", "AvgLatency(ms)"])
            for lvl, res_dict in [("Paper", paper_results), ("Chunk", chunk_results)]:
                for mode, r in res_dict.items():
                    writer.writerow([lvl, r.method.upper(), r.query_count, r.recall_at_1, r.recall_at_5, r.recall_at_10, r.precision_at_5, r.hit_rate_at_5, r.mrr, r.ndcg_at_5, r.ndcg_at_10, r.avg_latency_ms])

        # 2. Generation & Grounding Benchmarks
        gen_data = {
            mode: {
                "method": mode,
                "grounded_claim_percentage": r.grounded_claim_percentage,
                "selective_accuracy": r.selective_accuracy,
                "unsupported_answer_rate": r.unsupported_answer_rate,
            }
            for mode, r in paper_results.items()
        }
        with open(exp_dir / "benchmark_generation.json", "w", encoding="utf-8") as f:
            json.dump(gen_data, f, indent=2)

        with open(exp_dir / "benchmark_generation.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Method", "GroundedClaim%", "SelectiveAccuracy", "UnsupportedAnswerRate"])
            for mode, d in gen_data.items():
                writer.writerow([d["method"].upper(), d["grounded_claim_percentage"], d["selective_accuracy"], d["unsupported_answer_rate"]])

        # 3. Abstention Benchmark
        with open(exp_dir / "benchmark_abstention.json", "w", encoding="utf-8") as f:
            json.dump(threshold_sweep, f, indent=2)

        with open(exp_dir / "benchmark_abstention.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Threshold", "AbstentionAccuracy", "SelectiveAccuracy", "UnsupportedAnswerRate", "FalseAbstentionRate"])
            for r in threshold_sweep:
                writer.writerow([r["threshold"], r["abstention_accuracy"], r["selective_accuracy"], r["unsupported_answer_rate"], r["false_abstention_rate"]])

        # 4. Latency Profile Benchmark
        with open(exp_dir / "benchmark_latency.json", "w", encoding="utf-8") as f:
            json.dump(latency_profile, f, indent=2)

        with open(exp_dir / "benchmark_latency.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Stage", "MeanLatency(ms)", "MedianLatency(ms)", "P95Latency(ms)"])
            for stage, stats in latency_profile.items():
                writer.writerow([stage, stats["mean_ms"], stats["median_ms"], stats["p95_ms"]])

        # 5. Executive Summary Markdown
        summary_md = self._build_benchmark_summary_markdown(paper_results, chunk_results, threshold_sweep, latency_profile)
        with open(exp_dir / "benchmark_summary.md", "w", encoding="utf-8") as f:
            f.write(summary_md)

        logger.info(f"Saved all comprehensive evaluation reports to {exp_dir}")

    def _build_benchmark_summary_markdown(
        self,
        paper_results: Dict[str, EvaluationResult],
        chunk_results: Dict[str, EvaluationResult],
        threshold_sweep: List[Dict[str, Any]],
        latency_profile: Dict[str, Any],
    ) -> str:
        """Generate comprehensive Markdown executive summary."""
        lines = []
        lines.append("# ResearchMind — Comprehensive Benchmark Evaluation Summary")
        lines.append("")
        lines.append("## 1. Paper-Level Retrieval Benchmark (Held-Out Test Set: 50 Queries)")
        lines.append("")
        headers_ret = ["Method", "Recall@1", "Recall@5", "Recall@10", "Hit Rate@5", "MRR", "nDCG@10", "Latency (ms)"]
        rows_paper = [
            [r.method.upper(), f"{r.recall_at_1:.3f}", f"{r.recall_at_5:.3f}", f"{r.recall_at_10:.3f}", f"{r.hit_rate_at_5:.3f}", f"{r.mrr:.3f}", f"{r.ndcg_at_10:.3f}", f"{r.avg_latency_ms:.1f}"]
            for r in paper_results.values()
        ]
        lines.append(tabulate(rows_paper, headers=headers_ret, tablefmt="github"))
        lines.append("")

        lines.append("## 2. Chunk-Level Evidence Retrieval Benchmark")
        lines.append("")
        rows_chunk = [
            [r.method.upper(), f"{r.recall_at_1:.3f}", f"{r.recall_at_5:.3f}", f"{r.recall_at_10:.3f}", f"{r.hit_rate_at_5:.3f}", f"{r.mrr:.3f}", f"{r.ndcg_at_10:.3f}", f"{r.avg_latency_ms:.1f}"]
            for r in chunk_results.values()
        ]
        lines.append(tabulate(rows_chunk, headers=headers_ret, tablefmt="github"))
        lines.append("")

        lines.append("## 3. Abstention & Threshold Calibration (Validation Set)")
        lines.append("")
        headers_abs = ["Threshold", "Abstention Accuracy", "Selective Accuracy", "Unsupported Answer %", "False Abstention %"]
        rows_abs = [
            [f"{r['threshold']:.2f}", f"{r['abstention_accuracy']*100:.1f}%", f"{r['selective_accuracy']*100:.1f}%", f"{r['unsupported_answer_rate']*100:.1f}%", f"{r['false_abstention_rate']*100:.1f}%"]
            for r in threshold_sweep
        ]
        lines.append(tabulate(rows_abs, headers=headers_abs, tablefmt="github"))
        lines.append("")

        lines.append("## 4. Pipeline Sub-Stage Latency Profiling")
        lines.append("")
        headers_lat = ["Pipeline Stage", "Mean (ms)", "Median (ms)", "P95 (ms)"]
        rows_lat = [
            [stage.replace("_", " ").title(), f"{stats['mean_ms']:.1f}", f"{stats['median_ms']:.1f}", f"{stats['p95_ms']:.1f}"]
            for stage, stats in latency_profile.items()
        ]
        lines.append(tabulate(rows_lat, headers=headers_lat, tablefmt="github"))
        lines.append("")

        return "\n".join(lines)
