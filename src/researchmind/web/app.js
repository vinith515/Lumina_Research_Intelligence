/**
 * ResearchMind v2.0 - Interactive Dynamic RAG Web Dashboard
 */

document.addEventListener("DOMContentLoaded", () => {
  // -------------------------------------------------------------
  // Application State
  // -------------------------------------------------------------
  const state = {
    sessionId: localStorage.getItem("researchmind_session_id") || `session_${Math.random().toString(36).substring(2, 9)}`,
    activeScope: "global",
    targetPaperId: null,
    papers: [],
    jobs: new Map(),
    currentPdf: { paperId: null, page: 1, title: "" },
    onlineCandidates: [],
    selectedCandidateIds: new Set(),
    activeCitations: new Map(), // citationId -> StructuredCitation
    conversationHistory: [],
  };

  localStorage.setItem("researchmind_session_id", state.sessionId);

  // -------------------------------------------------------------
  // DOM Elements
  // -------------------------------------------------------------
  const sessionIdDisplay = document.getElementById("sessionIdDisplay");
  const corpusPaperCount = document.getElementById("corpusPaperCount");
  const scopeContainer = document.getElementById("scopeContainer");
  const targetPaperContainer = document.getElementById("targetPaperContainer");
  const targetPaperSelect = document.getElementById("targetPaperSelect");

  const uploadDropzone = document.getElementById("uploadDropzone");
  const fileInput = document.getElementById("fileInput");
  const ingestionJobsList = document.getElementById("ingestionJobsList");
  const indexedPapersList = document.getElementById("indexedPapersList");
  const sessionPapersCount = document.getElementById("sessionPapersCount");

  const queryForm = document.getElementById("queryForm");
  const queryInput = document.getElementById("queryInput");
  const btnSubmitQuery = document.getElementById("btnSubmitQuery");
  const chatViewport = document.getElementById("chatViewport");
  const messagesContainer = document.getElementById("messagesContainer");
  const welcomeCard = document.getElementById("welcomeCard");

  const evidencePromptBanner = document.getElementById("evidencePromptBanner");
  const evidencePromptDesc = document.getElementById("evidencePromptDesc");
  const btnAcceptOnlineSearch = document.getElementById("btnAcceptOnlineSearch");
  const btnDismissOnlineSearch = document.getElementById("btnDismissOnlineSearch");

  const viewerPaperTitle = document.getElementById("viewerPaperTitle");
  const currentPageNum = document.getElementById("currentPageNum");
  const btnPrevPage = document.getElementById("btnPrevPage");
  const btnNextPage = document.getElementById("btnNextPage");
  const btnOpenPdfTab = document.getElementById("btnOpenPdfTab");
  const pdfFrame = document.getElementById("pdfFrame");
  const viewerPlaceholder = document.getElementById("viewerPlaceholder");

  const passageInspector = document.getElementById("passageInspector");
  const inspectorCitationId = document.getElementById("inspectorCitationId");
  const inspectorSection = document.getElementById("inspectorSection");
  const inspectorSnippet = document.getElementById("inspectorSnippet");
  const inspectorPage = document.getElementById("inspectorPage");
  const inspectorScore = document.getElementById("inspectorScore");
  const btnCloseInspector = document.getElementById("btnCloseInspector");

  const btnOpenOnlineSearch = document.getElementById("btnOpenOnlineSearch");
  const onlineSearchModal = document.getElementById("onlineSearchModal");
  const btnCloseModal = document.getElementById("btnCloseModal");
  const btnCancelModal = document.getElementById("btnCancelModal");
  const onlineSearchQuery = document.getElementById("onlineSearchQuery");
  const onlineSearchProvider = document.getElementById("onlineSearchProvider");
  const btnExecuteOnlineSearch = document.getElementById("btnExecuteOnlineSearch");
  const onlineSearchResults = document.getElementById("onlineSearchResults");
  const selectedCandidatesCount = document.getElementById("selectedCandidatesCount");
  const btnIngestSelectedCandidates = document.getElementById("btnIngestSelectedCandidates");

  let suggestedOnlineQuery = "";

  // -------------------------------------------------------------
  // Initialization
  // -------------------------------------------------------------
  sessionIdDisplay.textContent = state.sessionId;
  loadHealthAndCorpus();
  loadPapers();
  pollActiveJobs();

  // -------------------------------------------------------------
  // Event Listeners: Knowledge Scope Selector
  // -------------------------------------------------------------
  scopeContainer.querySelectorAll(".scope-card").forEach((card) => {
    card.addEventListener("click", () => {
      scopeContainer.querySelectorAll(".scope-card").forEach((c) => c.classList.remove("active"));
      card.classList.add("active");
      const radio = card.querySelector("input[type='radio']");
      radio.checked = true;
      state.activeScope = card.getAttribute("data-scope");

      if (state.activeScope === "this_paper") {
        targetPaperContainer.style.display = "flex";
      } else {
        targetPaperContainer.style.display = "none";
      }
    });
  });

  targetPaperSelect.addEventListener("change", (e) => {
    state.targetPaperId = e.target.value || null;
  });

  // Suggestion chips
  document.querySelectorAll(".suggestion-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      queryInput.value = chip.getAttribute("data-query");
      queryInput.focus();
    });
  });

  // -------------------------------------------------------------
  // File Upload Handlers (Drag & Drop + File Dialog)
  // -------------------------------------------------------------
  uploadDropzone.addEventListener("click", () => fileInput.click());

  uploadDropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    uploadDropzone.classList.add("dragover");
  });

  uploadDropzone.addEventListener("dragleave", () => {
    uploadDropzone.classList.remove("dragover");
  });

  uploadDropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadDropzone.classList.remove("dragover");
    if (e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      handleFileUpload(e.target.files[0]);
      fileInput.value = "";
    }
  });

  async function handleFileUpload(file) {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      alert("Please upload a valid PDF file.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("session_id", state.sessionId);

    try {
      const resp = await fetch("/api/papers/upload", {
        method: "POST",
        body: formData,
      });

      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || "Upload failed");
      }

      const data = await resp.json();
      registerIngestionJob({
        job_id: data.job_id,
        file_name: data.file_name,
        status: data.status,
        progress_pct: 0,
        current_stage: "PARSING",
      });
    } catch (err) {
      alert(`Upload error: ${err.message}`);
    }
  }

  // -------------------------------------------------------------
  // Ingestion Job Management & Polling
  // -------------------------------------------------------------
  function registerIngestionJob(job) {
    state.jobs.set(job.job_id, job);
    renderJobs();
    pollJob(job.job_id);
  }

  function renderJobs() {
    if (state.jobs.size === 0) {
      ingestionJobsList.innerHTML = "";
      return;
    }

    let html = "";
    state.jobs.forEach((job) => {
      let badgeClass = "processing";
      if (job.status === "completed") badgeClass = "completed";
      if (job.status === "failed") badgeClass = "failed";

      html += `
        <div class="job-card" id="job_${job.job_id}">
          <div class="job-header">
            <span class="job-filename" title="${job.file_name}">${job.file_name}</span>
            <span class="job-badge ${badgeClass}">${job.status}</span>
          </div>
          <div class="job-progress-bar">
            <div class="job-progress-fill" style="width: ${job.progress_pct || (job.status === 'completed' ? 100 : 20)}%"></div>
          </div>
          <div class="job-meta">
            <span>${job.current_stage || job.status}</span>
            <span>${job.chunk_count ? job.chunk_count + ' chunks' : ''}</span>
          </div>
        </div>
      `;
    });
    ingestionJobsList.innerHTML = html;
  }

  async function pollJob(jobId) {
    const interval = setInterval(async () => {
      try {
        const resp = await fetch(`/api/ingestion/${jobId}`);
        if (!resp.ok) {
          clearInterval(interval);
          return;
        }
        const updated = await resp.json();
        state.jobs.set(jobId, updated);
        renderJobs();

        if (updated.status === "completed" || updated.status === "failed") {
          clearInterval(interval);
          loadPapers(); // Refresh paper list
        }
      } catch (e) {
        clearInterval(interval);
      }
    }, 1500);
  }

  async function pollActiveJobs() {
    try {
      const resp = await fetch(`/api/ingestion?session_id=${state.sessionId}`);
      if (resp.ok) {
        const jobs = await resp.json();
        jobs.forEach((job) => {
          state.jobs.set(job.job_id, job);
          if (job.status !== "completed" && job.status !== "failed") {
            pollJob(job.job_id);
          }
        });
        renderJobs();
      }
    } catch (e) {
      console.warn("Could not poll active jobs", e);
    }
  }

  // -------------------------------------------------------------
  // Data Fetching: Health & Papers
  // -------------------------------------------------------------
  async function loadHealthAndCorpus() {
    try {
      const resp = await fetch("/api/health");
      if (resp.ok) {
        const data = await resp.json();
        corpusPaperCount.textContent = `Corpus: ${data.baseline_papers_count} Papers`;
      }
    } catch (e) {
      corpusPaperCount.textContent = "Offline Mode";
    }
  }

  async function loadPapers() {
    try {
      const resp = await fetch(`/api/papers?session_id=${state.sessionId}`);
      if (resp.ok) {
        const data = await resp.json();
        state.papers = data.papers || [];

        // Update target paper select
        targetPaperSelect.innerHTML = `<option value="">-- Select a target paper --</option>` +
          state.papers.map(p => `<option value="${p.paper_id}">${p.title} (${p.category})</option>`).join("");

        // Update Session Uploaded Papers in Sidebar
        const sessionUploads = state.papers.filter(p => p.is_user_uploaded);
        sessionPapersCount.textContent = sessionUploads.length;

        if (sessionUploads.length === 0) {
          indexedPapersList.innerHTML = `<div class="empty-state-small">No custom papers uploaded yet in this session.</div>`;
        } else {
          indexedPapersList.innerHTML = sessionUploads.map(p => `
            <div class="paper-item" data-id="${p.paper_id}">
              <div class="paper-item-title" title="${p.title}">${p.title}</div>
              <span class="paper-item-chunks">${p.total_chunks} chunks</span>
            </div>
          `).join("");

          indexedPapersList.querySelectorAll(".paper-item").forEach(item => {
            item.addEventListener("click", () => {
              const pid = item.getAttribute("data-id");
              const paper = state.papers.find(x => x.paper_id === pid);
              if (paper) {
                loadPdfInViewer(pid, 1, paper.title);
              }
            });
          });
        }
      }
    } catch (e) {
      console.error("Error loading papers", e);
    }
  }

  // -------------------------------------------------------------
  // Query Execution & Grounded Generation
  // -------------------------------------------------------------
  queryForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = queryInput.value.trim();
    if (!query) return;

    // Validate 'this_paper' scope selection
    if (state.activeScope === "this_paper" && !state.targetPaperId) {
      alert("Please select a target paper from the dropdown before querying in 'This Paper Only' scope.");
      return;
    }

    welcomeCard.style.display = "none";
    evidencePromptBanner.style.display = "none";

    // Append User Question to Viewport
    appendUserMessage(query);
    queryInput.value = "";
    btnSubmitQuery.disabled = true;

    // Loading Card
    const loadingCardId = `loading_${Date.now()}`;
    appendLoadingCard(loadingCardId);

    state.conversationHistory.push({ role: "user", content: query });

    const payload = {
      query: query,
      knowledge_scope: state.activeScope,
      scope_paper_ids: state.activeScope === "this_paper" && state.targetPaperId ? [state.targetPaperId] : null,
      session_id: state.sessionId,
      top_k: 5,
      retrieval_mode: "hybrid_rerank",
      conversation_history: state.conversationHistory.slice(-10),
    };

    try {
      const resp = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      removeCard(loadingCardId);
      btnSubmitQuery.disabled = false;

      if (!resp.ok) {
        const err = await resp.json();
        appendErrorMessage(err.detail || "Query failed");
        return;
      }

      const result = await resp.json();
      state.conversationHistory.push({
        role: "assistant",
        content: result.answer,
        target_paper_id: result.target_paper_id,
        target_paper_title: result.target_paper_title,
      });
      appendAssistantMessage(result);

      // Check evidence sufficiency
      if (result.online_search_suggested) {
        suggestedOnlineQuery = result.suggested_query || query;
        evidencePromptDesc.textContent = `Local corpus lacks sufficient evidence (Relevance < 0.35). Search arXiv & Semantic Scholar for: "${suggestedOnlineQuery}"?`;
        evidencePromptBanner.style.display = "flex";
      }
    } catch (err) {
      removeCard(loadingCardId);
      btnSubmitQuery.disabled = false;
      appendErrorMessage(err.message || "Network error");
    }
  });

  function appendUserMessage(text) {
    const div = document.createElement("div");
    div.className = "message-card";
    div.innerHTML = `
      <div class="message-header">
        <span class="message-query-text">Question</span>
        <span class="evidence-badge moderate">${state.activeScope.toUpperCase()}</span>
      </div>
      <div class="message-body" style="font-weight: 500;">${escapeHtml(text)}</div>
    `;
    messagesContainer.appendChild(div);
    chatViewport.scrollTop = chatViewport.scrollHeight;
  }

  function appendLoadingCard(id) {
    const div = document.createElement("div");
    div.id = id;
    div.className = "message-card";
    div.innerHTML = `
      <div class="message-header">
        <span class="message-query-text">Synthesizing Grounded Evidence...</span>
      </div>
      <div class="message-body" style="color: var(--text-muted); font-size: 0.85rem;">
        Searching vector index, performing BM25 keyword matching, reciprocal rank fusion, and cross-encoder verification...
      </div>
    `;
    messagesContainer.appendChild(div);
    chatViewport.scrollTop = chatViewport.scrollHeight;
  }

  function removeCard(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  function appendErrorMessage(msg) {
    const div = document.createElement("div");
    div.className = "message-card";
    div.innerHTML = `
      <div class="message-header">
        <span class="message-query-text" style="color: var(--accent-rose);">Error</span>
      </div>
      <div class="message-body" style="color: var(--accent-rose);">${escapeHtml(msg)}</div>
    `;
    messagesContainer.appendChild(div);
    chatViewport.scrollTop = chatViewport.scrollHeight;
  }

  function appendAssistantMessage(res) {
    const div = document.createElement("div");
    div.className = "message-card";

    // Cache citations for viewer clicking
    if (res.structured_citations && res.structured_citations.length > 0) {
      res.structured_citations.forEach((sc) => {
        state.activeCitations.set(sc.id, sc);
      });
    }

    // Format Answer Body with interactive citation badges [C1], [C2]
    let formattedAnswer = formatMarkdown(res.answer);
    formattedAnswer = formattedAnswer.replace(/\[C(\d+)\]/g, (match, num) => {
      const citationId = `C${num}`;
      return `<span class="citation-pill" data-citation-id="${citationId}">${match}</span>`;
    });

    let evidenceClass = "moderate";
    if (res.evidence_state.toLowerCase() === "strong") evidenceClass = "strong";
    if (res.evidence_state.toLowerCase() === "insufficient") evidenceClass = "insufficient";

    let citationsHtml = "";
    if (res.structured_citations && res.structured_citations.length > 0) {
      citationsHtml = `
        <div class="citations-footer">
          <div class="citations-footer-title">Verified Grounded Sources (${res.structured_citations.length})</div>
          <div class="citations-cards-grid">
            ${res.structured_citations.map(sc => `
              <div class="citation-summary-card" data-citation-id="${sc.id}">
                <div class="citation-card-left">
                  <span class="citation-tag">[${sc.id}]</span>
                  <span class="citation-paper-title">${escapeHtml(sc.paper_title)}</span>
                </div>
                <div class="citation-meta-pill">
                  Page ${sc.viewer_reference.page_number} • ${Math.round(sc.relevance_score * 100)}% Match
                </div>
              </div>
            `).join("")}
          </div>
        </div>
      `;
    }

    div.innerHTML = `
      <div class="message-header">
        <span class="message-query-text">Grounded Answer</span>
        <div class="message-meta">
          <span class="evidence-badge ${evidenceClass}">Evidence: ${res.evidence_state.toUpperCase()}</span>
          <span style="font-size: 0.72rem; color: var(--text-muted);">${res.latency_ms} ms</span>
        </div>
      </div>
      <div class="message-body">${formattedAnswer}</div>
      ${citationsHtml}
    `;

    // Attach click listeners to citation pills & summary cards
    div.querySelectorAll(".citation-pill, .citation-summary-card").forEach((el) => {
      el.addEventListener("click", () => {
        const cid = el.getAttribute("data-citation-id");
        activateCitation(cid);
      });
    });

    messagesContainer.appendChild(div);
    chatViewport.scrollTop = chatViewport.scrollHeight;
  }

  // -------------------------------------------------------------
  // PDF Viewer & Passage Inspector Synchronization
  // -------------------------------------------------------------
  function activateCitation(citationId) {
    const citation = state.activeCitations.get(citationId);
    if (!citation || !citation.viewer_reference) {
      console.warn("No viewer reference found for citation", citationId);
      return;
    }

    const ref = citation.viewer_reference;
    loadPdfInViewer(ref.paper_id, ref.page_number, citation.paper_title);

    // Update inspector drawer
    inspectorCitationId.textContent = `[${citation.id}]`;
    inspectorSection.textContent = citation.paper_title;
    inspectorSnippet.textContent = `"${ref.snippet || citation.snippet}"`;
    inspectorPage.textContent = `Page ${ref.page_number}`;
    inspectorScore.textContent = `Relevance: ${(citation.relevance_score || 0).toFixed(2)}`;
    passageInspector.style.display = "flex";
  }

  function loadPdfInViewer(paperId, page = 1, title = "") {
    state.currentPdf.paperId = paperId;
    state.currentPdf.page = page;
    state.currentPdf.title = title || paperId;

    viewerPaperTitle.textContent = state.currentPdf.title;
    currentPageNum.textContent = page;

    viewerPlaceholder.style.display = "none";
    pdfFrame.style.display = "block";

    // Set iframe source with page target anchor
    const pdfUrl = `/api/papers/${paperId}/pdf#page=${page}`;
    pdfFrame.src = pdfUrl;
    btnOpenPdfTab.href = pdfUrl;
  }

  btnPrevPage.addEventListener("click", () => {
    if (state.currentPdf.paperId && state.currentPdf.page > 1) {
      state.currentPdf.page--;
      loadPdfInViewer(state.currentPdf.paperId, state.currentPdf.page, state.currentPdf.title);
    }
  });

  btnNextPage.addEventListener("click", () => {
    if (state.currentPdf.paperId) {
      state.currentPdf.page++;
      loadPdfInViewer(state.currentPdf.paperId, state.currentPdf.page, state.currentPdf.title);
    }
  });

  btnCloseInspector.addEventListener("click", () => {
    passageInspector.style.display = "none";
  });

  // -------------------------------------------------------------
  // Online Research Discovery Modal & External Search Flow
  // -------------------------------------------------------------
  btnOpenOnlineSearch.addEventListener("click", () => {
    openOnlineModal("");
  });

  btnAcceptOnlineSearch.addEventListener("click", () => {
    evidencePromptBanner.style.display = "none";
    openOnlineModal(suggestedOnlineQuery);
  });

  btnDismissOnlineSearch.addEventListener("click", () => {
    evidencePromptBanner.style.display = "none";
  });

  function openOnlineModal(initialQuery = "") {
    onlineSearchModal.style.display = "flex";
    if (initialQuery) {
      onlineSearchQuery.value = initialQuery;
      executeOnlineSearch();
    } else {
      onlineSearchQuery.focus();
    }
  }

  function closeOnlineModal() {
    onlineSearchModal.style.display = "none";
  }

  btnCloseModal.addEventListener("click", closeOnlineModal);
  btnCancelModal.addEventListener("click", closeOnlineModal);

  btnExecuteOnlineSearch.addEventListener("click", executeOnlineSearch);
  onlineSearchQuery.addEventListener("keydown", (e) => {
    if (e.key === "Enter") executeOnlineSearch();
  });

  async function executeOnlineSearch() {
    const q = onlineSearchQuery.value.trim();
    if (!q) return;

    btnExecuteOnlineSearch.disabled = true;
    onlineSearchResults.innerHTML = `<div class="empty-state">Querying arXiv Atom API & Semantic Scholar Graph API...</div>`;

    try {
      const resp = await fetch("/api/papers/search-online", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: q,
          provider: onlineSearchProvider.value,
          max_results: 5,
        }),
      });

      btnExecuteOnlineSearch.disabled = false;
      if (!resp.ok) {
        throw new Error("Online search request failed");
      }

      const data = await resp.json();
      state.onlineCandidates = data.candidates || [];
      state.selectedCandidateIds.clear();
      renderCandidateResults();
    } catch (err) {
      btnExecuteOnlineSearch.disabled = false;
      onlineSearchResults.innerHTML = `<div class="empty-state" style="color: var(--accent-rose);">${err.message}</div>`;
    }
  }

  function renderCandidateResults() {
    if (state.onlineCandidates.length === 0) {
      onlineSearchResults.innerHTML = `<div class="empty-state">No matching scientific papers found. Try a different query.</div>`;
      updateSelectedCount();
      return;
    }

    onlineSearchResults.innerHTML = state.onlineCandidates.map((c) => {
      const isAlready = c.already_in_corpus;
      return `
        <div class="candidate-card ${isAlready ? 'already-indexed' : ''}" data-cid="${c.id}">
          <input type="checkbox" class="candidate-checkbox" value="${c.id}" ${isAlready ? 'disabled' : ''}>
          <div class="candidate-info">
            <div class="candidate-title">${escapeHtml(c.title)}</div>
            <div class="candidate-authors">${c.authors.slice(0, 3).join(", ")}${c.authors.length > 3 ? ' et al.' : ''} • ${c.year || '2026'}</div>
            <div class="candidate-abstract">${escapeHtml(c.abstract || 'No abstract preview available.')}</div>
            <div class="candidate-meta">
              <span class="candidate-source-tag">${c.source_provider}</span>
              ${isAlready ? '<span class="scope-badge green">Already in Corpus</span>' : ''}
              ${c.pdf_url ? '<span class="scope-badge blue">PDF Available</span>' : '<span class="scope-badge rose">No PDF</span>'}
              <span>Relevance: ${(c.relevance_score || 0).toFixed(2)}</span>
            </div>
          </div>
        </div>
      `;
    }).join("");

    onlineSearchResults.querySelectorAll(".candidate-checkbox").forEach((cb) => {
      cb.addEventListener("change", (e) => {
        if (e.target.checked) {
          state.selectedCandidateIds.add(e.target.value);
        } else {
          state.selectedCandidateIds.delete(e.target.value);
        }
        updateSelectedCount();
      });
    });

    updateSelectedCount();
  }

  function updateSelectedCount() {
    const count = state.selectedCandidateIds.size;
    selectedCandidatesCount.textContent = count;
    btnIngestSelectedCandidates.disabled = count === 0;
  }

  btnIngestSelectedCandidates.addEventListener("click", async () => {
    const selected = state.onlineCandidates.filter((c) => state.selectedCandidateIds.has(c.id));
    if (selected.length === 0) return;

    btnIngestSelectedCandidates.disabled = true;
    btnIngestSelectedCandidates.textContent = "Ingesting...";

    try {
      const resp = await fetch("/api/papers/ingest-online", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          candidates: selected,
          session_id: state.sessionId,
        }),
      });

      if (!resp.ok) {
        throw new Error("Online paper ingestion failed");
      }

      const res = await resp.json();
      (res.jobs || []).forEach((job) => {
        registerIngestionJob({
          job_id: job.job_id,
          file_name: job.file_name,
          status: job.status,
          progress_pct: 0,
          current_stage: "DOWNLOADING",
        });
      });

      closeOnlineModal();
      btnIngestSelectedCandidates.disabled = false;
      btnIngestSelectedCandidates.textContent = "Ingest Selected Papers";
    } catch (err) {
      alert(`Ingestion error: ${err.message}`);
      btnIngestSelectedCandidates.disabled = false;
      btnIngestSelectedCandidates.textContent = "Ingest Selected Papers";
    }
  });

  // -------------------------------------------------------------
  // Helpers
  // -------------------------------------------------------------
  function escapeHtml(text) {
    if (!text) return "";
    return text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function formatMarkdown(text) {
    if (!text) return "";
    let html = escapeHtml(text);
    // Bold **text**
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    // Bullet points
    html = html.replace(/^\* (.*$)/gim, "<li>$1</li>");
    html = html.replace(/^- (.*$)/gim, "<li>$1</li>");
    // Paragraph newlines
    html = html.replace(/\n\n/g, "<br><br>");
    return html;
  }
});
