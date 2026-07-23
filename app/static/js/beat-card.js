function formatDate(dateString) {
  if (!dateString) return "Unknown date";

  const date = new Date(dateString);
  if (isNaN(date.getTime())) return dateString;

  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric"
  });
}

function createBeatCard(beat) {
  const creatorId = beat.creator_id ?? null;
  const creatorName = beat.creator_name ?? "Unknown Creator";
  const creatorHref = creatorId !== null ? `/creator/${creatorId}` : "#";

  return `
    <div class="beat-card">
      <div class="cover">
        <div class="beat-card-menu-wrap">
          <button class="beat-card-menu-btn" type="button" aria-label="Open beat options" data-beat-id="${beat.id}">
            ⋯
          </button>
          <div class="beat-card-menu" role="menu">
            <button class="beat-card-menu-item report-btn" type="button" data-beat-id="${beat.id}">
              Report
            </button>
          </div>
        </div>

        <button class="cover-play-btn play-btn" type="button" data-url="${beat.url}">
          ▶
        </button>
      </div>

      <div class="beat-content">
        <span class="genre">${beat.genre || "Unknown"}</span>
        <h3>${beat.title || "Untitled Beat"}</h3>

        <div class="beat-meta">
          <a class="creator-id" href="${creatorHref}">
            By ${creatorName}
          </a>
          <span class="work-price">EGP${parseFloat(beat.price || 0).toFixed(2)}</span>
        </div>

        <p>
          Published: ${formatDate(beat.date_published)}<br>
          Likes: <span class="likes-count">${beat.likes ?? 0}</span> • 
          Views: ${beat.views ?? 0}
        </p>

        <div class="action-row">
          <button 
            class="action-btn save-btn ${beat.saved ? "active" : ""}" 
            type="button"
            data-beat-id="${beat.id}"
            data-saved="${beat.saved ? "true" : "false"}"
          >
            ${beat.saved ? "Saved" : "Save"}
          </button>

          <button 
            class="action-btn add-cart-btn" 
            type="button"
            data-beat-id="${beat.id}"
            data-added="${beat.added ? "true" : "false"}"
          >
            ${beat.added ? "Added" : "Cart"}
          </button>

          <button 
            class="action-btn like-btn ${beat.liked ? "active" : ""}" 
            type="button"
            data-beat-id="${beat.id}"
            data-liked="${beat.liked ? "true" : "false"}"
          >
            ${beat.liked ? "Liked" : "Like"}
          </button>
        </div>

        <progress class="audio-progress" value="0" max="100"></progress>
        <audio class="hidden-audio" preload="none" src="${beat.url}"></audio>
      </div>
    </div>
  `;
}

function attachProgressBar(root) {
  const cards = root.querySelectorAll(".beat-card");
  
  cards.forEach(card => {
    const progress = card.querySelector(".audio-progress");
    const audio = card.querySelector(".hidden-audio");
    
    if (!progress || !audio || progress.dataset.bound === "true") return;
    progress.dataset.bound = "true";

    audio.addEventListener("play", () => {
      progress.style.display = "block";
    });

    audio.addEventListener("pause", () => {
      progress.style.display = "none";
    });

    audio.addEventListener("timeupdate", () => {
      if (audio.duration) {
        progress.value = (audio.currentTime / audio.duration) * 100;
      }
    });

    audio.addEventListener("ended", () => {
      progress.value = 0;
      progress.style.display = "none";
    });

    progress.addEventListener("click", (e) => {
      const rect = progress.getBoundingClientRect();
      const percent = (e.clientX - rect.left) / rect.width;
      audio.currentTime = percent * audio.duration;
    });
  });
}


function attachPlayEvents(root = document) {
  const playButtons = root.querySelectorAll(".play-btn");

  playButtons.forEach(button => {
    if (button.dataset.bound === "true") return;
    button.dataset.bound = "true";

    button.addEventListener("click", function () {
      const card = this.closest(".beat-card");
      const audio = card.querySelector(".hidden-audio");

      document.querySelectorAll(".hidden-audio").forEach(player => {
        if (player !== audio) {
          player.pause();
          player.currentTime = 0;
          player.classList.remove("active");
        }
      });

      document.querySelectorAll(".play-btn").forEach(btn => {
        if (btn !== this) {
          btn.textContent = "▶";
          btn.classList.remove("active");
        }
      });

      if (audio.classList.contains("active") && !audio.paused) {
        audio.pause();
        audio.currentTime = 0;
        this.textContent = "▶";
        this.classList.remove("active");
        audio.classList.remove("active");
      } else {
        audio.classList.add("active");
        audio.play().catch(err => {
          console.error(err);
        });
        this.textContent = "⏹";
        this.classList.add("active");
      }

      audio.onended = () => {
        audio.classList.remove("active");
        this.textContent = "▶";
        this.classList.remove("active");
      };
    });
  });
}

function attachCartEvents(root = document) {
  const cartButtons = root.querySelectorAll(".add-cart-btn");

  cartButtons.forEach(button => {
    if (button.dataset.bound === "true") return;
    button.dataset.bound = "true";

    if (button.dataset.added === "true") {
      button.classList.add("active");
    }

    button.addEventListener("click", async function () {
      const beatId = this.dataset.beatId;
      const isAdded = this.dataset.added === "true";

      if (!beatId) return;
      this.disabled = true;

      const originalText = this.textContent;

      try {
        const response = await fetch(
          isAdded ? `/cart/remove_cart/${beatId}` : `/cart/add_cart/${beatId}`,
          {
            method: isAdded ? "DELETE" : "POST",
            credentials: "include"
          }
        );

        if (!response.ok) {
          if (response.status === 401) {
            showLoginPrompt();
            this.disabled = false;
            return;
          }
          this.disabled = false;
          return;
        }
        this.disabled = false;

        if (isAdded) {
          this.dataset.added = "false";
          this.classList.remove("active");
          this.textContent = "Cart";
        } else {
          this.dataset.added = "true";
          this.classList.add("active");
          this.textContent = "Added";
        }

      } catch (error) {
        this.textContent = "Error";
        this.disabled = false;
      }
    });
  });
}

function attachLikeEvents(root = document) {
  const likeButtons = root.querySelectorAll(".like-btn");

  likeButtons.forEach(button => {
    if (button.dataset.bound === "true") return;
    button.dataset.bound = "true";

    button.addEventListener("click", async function () {
      const beatId = this.dataset.beatId;
      const isLiked = this.dataset.liked === "true";
      const likesCountElement = this.closest(".beat-content").querySelector(".likes-count");

      if (!beatId || !likesCountElement) return;

      this.disabled = true;

      try {
        const response = await fetch(
          isLiked ? `/users/unlike/${beatId}` : `/users/like/${beatId}`,
          {
            method: isLiked ? "DELETE" : "POST",
            credentials: "include"
          }
        );

        if (!response.ok) {
          if (response.status === 401) {
            showLoginPrompt();
            this.disabled = false;
            return;
          }
          this.disabled = false;
          return;
        }

        let likesCount = parseInt(likesCountElement.textContent, 10) || 0;

        if (isLiked) {
          this.dataset.liked = "false";
          this.classList.remove("active");
          this.textContent = "Like";
        } else {
          this.dataset.liked = "true";
          this.classList.add("active");
          this.textContent = "Liked";
        }
      } catch (error) {
        this.textContent = "Error";
      }

      this.disabled = false;
    });
  });
}

function attachSaveEvents(root = document) {
  const saveButtons = root.querySelectorAll(".save-btn");

  saveButtons.forEach(button => {
    if (button.dataset.bound === "true") return;
    button.dataset.bound = "true";

    button.addEventListener("click", async function () {
      const beatId = this.dataset.beatId;
      const isSaved = this.dataset.saved === "true";

      if (!beatId) return;

      this.disabled = true;

      try {
        const response = await fetch(
          isSaved ? `/users/unsave/${beatId}` : `/users/save/${beatId}`,
          {
            method: isSaved ? "DELETE" : "POST",
            credentials: "include"
          }
        );

        if (!response.ok) {
          if (response.status === 401) {
            showLoginPrompt();
            this.disabled = false;
            return;
          }
          this.disabled = false;
          return;
        }

        if (isSaved) {
          this.dataset.saved = "false";
          this.classList.remove("active");
          this.textContent = "Save";
        } else {
          this.dataset.saved = "true";
          this.classList.add("active");
          this.textContent = "Saved";
        }
      } catch (error) {
        console.error(error);
      }

      this.disabled = false;
    });
  });
}

function closeAllBeatMenus() {
  document.querySelectorAll(".beat-card-menu").forEach(menu => {
    menu.classList.remove("active");
  });
}

function attachBeatMenuEvents(root = document) {
  const menuButtons = root.querySelectorAll(".beat-card-menu-btn");

  menuButtons.forEach(button => {
    if (button.dataset.bound === "true") return;
    button.dataset.bound = "true";

    button.addEventListener("click", function (event) {
      event.stopPropagation();

      const wrap = this.closest(".beat-card-menu-wrap");
      const menu = wrap ? wrap.querySelector(".beat-card-menu") : null;

      closeAllBeatMenus();
      if (menu) {
        menu.classList.add("active");
      }
    });
  });

  const reportButtons = root.querySelectorAll(".report-btn");

  reportButtons.forEach(button => {
    if (button.dataset.bound === "true") return;
    button.dataset.bound = "true";

    button.addEventListener("click", function (event) {
      event.stopPropagation();
      const beatId = this.dataset.beatId;
      closeAllBeatMenus();
      showReportModal(beatId);
    });
  });

  if (document.body.dataset.beatMenuGlobalBound !== "true") {
    document.body.dataset.beatMenuGlobalBound = "true";
    document.addEventListener("click", (event) => {
      if (!event.target.closest(".beat-card-menu-wrap")) {
        closeAllBeatMenus();
      }
    });
  }
}

async function loadUserWorksForReport() {
  const worksWrap = document.getElementById("reportStealingWorksWrap");
  const worksSelect = document.getElementById("reportUserBeatSelect");
  const worksStatus = document.getElementById("reportWorksStatus");

  if (!worksWrap || !worksSelect || !worksStatus) return;

  worksSelect.disabled = true;
  worksSelect.innerHTML = '<option value="">Loading your beats...</option>';
  worksStatus.textContent = "";

  try {
    const response = await fetch("/myworks/show_works", {
      credentials: "include"
    });

    if (!response.ok) {
      throw new Error("Unable to load your beats");
    }

    const beats = await response.json();
    worksSelect.innerHTML = '<option value="">Select one of your beats</option>';

    if (!Array.isArray(beats) || !beats.length) {
      worksSelect.innerHTML = '<option value="">No beats found</option>';
      worksStatus.textContent = "You do not have any beats to select.";
      return;
    }

    beats.forEach((beat) => {
      const option = document.createElement("option");
      option.value = beat.id;
      option.textContent = beat.title || `Beat #${beat.id}`;
      worksSelect.appendChild(option);
    });

    worksSelect.disabled = false;
  } catch (error) {
    worksSelect.innerHTML = '<option value="">Unable to load beats</option>';
    worksStatus.textContent = "We could not load your beats right now.";
  }
}

function resetReportModalForm() {
  const form = document.getElementById("reportModalForm");
  const subjectInputs = document.querySelectorAll(".report-subject-option-input");
  const worksWrap = document.getElementById("reportStealingWorksWrap");
  const worksSelect = document.getElementById("reportUserBeatSelect");
  const messageBox = document.getElementById("reportModalMessage");

  if (form) {
    form.reset();
  }

  subjectInputs.forEach((input) => {
    input.checked = false;
  });

  if (worksWrap) {
    worksWrap.hidden = true;
  }

  if (worksSelect) {
    worksSelect.innerHTML = '<option value="">Select one of your beats</option>';
    worksSelect.value = "";
    worksSelect.disabled = true;
  }

  if (messageBox) {
    messageBox.textContent = "";
    messageBox.className = "report-modal-message";
  }
}

function showReportModal(beatId) {
  if (!beatId) return;

  let modal = document.getElementById("reportModal");

  if (!modal) {
    const modalHTML = `
      <div id="reportModal" class="report-modal-overlay">
        <div class="report-modal">
          <button class="report-modal-close" type="button" id="reportModalCloseBtn" aria-label="Close report modal">×</button>
          <h2>Report Beat</h2>
          <p>Let us know why this beat should be reviewed.</p>
          <form id="reportModalForm" class="report-modal-form">
            <input type="hidden" id="reportBeatId" />
            <div class="report-subject-options">
              <label class="report-subject-option">
                <input class="report-subject-option-input" type="checkbox" name="reportSubject" value="stealing content" />
                <span>Stealing content</span>
              </label>
              <label class="report-subject-option">
                <input class="report-subject-option-input" type="checkbox" name="reportSubject" value="spam" />
                <span>Spam</span>
              </label>
              <label class="report-subject-option">
                <input class="report-subject-option-input" type="checkbox" name="reportSubject" value="inappropriate content" />
                <span>Inappropriate content</span>
              </label>
              <label class="report-subject-option">
                <input class="report-subject-option-input" type="checkbox" name="reportSubject" value="misleading content" />
                <span>Misleading content</span>
              </label>
            </div>

            <div id="reportStealingWorksWrap" class="report-works-wrap" hidden>
              <label for="reportUserBeatSelect">Choose one of your beats</label>
              <select id="reportUserBeatSelect" class="report-works-select" disabled>
                <option value="">Select one of your beats</option>
              </select>
              <div id="reportWorksStatus" class="report-works-status"></div>
            </div>

            <label for="reportBody">Details</label>
            <textarea id="reportBody" class="report-modal-textarea" rows="6" maxlength="500" placeholder="Add more context..."></textarea>
            <div id="reportModalMessage" class="report-modal-message"></div>
            <div class="report-modal-actions">
              <button class="report-modal-btn primary" type="submit" id="reportModalSubmitBtn">Submit</button>
              <button class="report-modal-btn secondary" type="button" id="reportModalCancelBtn">Cancel</button>
            </div>
          </form>
        </div>
      </div>
    `;

    document.body.insertAdjacentHTML("beforeend", modalHTML);
    modal = document.getElementById("reportModal");

    document.getElementById("reportModalCloseBtn").addEventListener("click", closeReportModal);
    document.getElementById("reportModalCancelBtn").addEventListener("click", closeReportModal);

    document.querySelectorAll(".report-subject-option-input").forEach((input) => {
      input.addEventListener("change", function () {
        const worksWrap = document.getElementById("reportStealingWorksWrap");
        const worksSelect = document.getElementById("reportUserBeatSelect");

        document.querySelectorAll(".report-subject-option-input").forEach((otherInput) => {
          if (otherInput !== this) {
            otherInput.checked = false;
          }
        });

        if (!this.checked) {
          if (worksWrap) worksWrap.hidden = true;
          if (worksSelect) {
            worksSelect.innerHTML = '<option value="">Select one of your beats</option>';
            worksSelect.value = "";
            worksSelect.disabled = true;
          }
          return;
        }

        if (this.value === "stealing content") {
          if (worksWrap) worksWrap.hidden = false;
          loadUserWorksForReport();
        } else {
          if (worksWrap) worksWrap.hidden = true;
          if (worksSelect) {
            worksSelect.innerHTML = '<option value="">Select one of your beats</option>';
            worksSelect.value = "";
            worksSelect.disabled = true;
          }
        }
      });
    });

    document.getElementById("reportModalForm").addEventListener("submit", async function (event) {
      event.preventDefault();

      const beatIdInput = document.getElementById("reportBeatId");
      const bodyInput = document.getElementById("reportBody");
      const submitBtn = document.getElementById("reportModalSubmitBtn");
      const messageBox = document.getElementById("reportModalMessage");
      const selectedSubjectInput = document.querySelector(".report-subject-option-input:checked");
      const worksSelect = document.getElementById("reportUserBeatSelect");

      if (!beatIdInput || !bodyInput || !messageBox) return;

      const subject = selectedSubjectInput ? selectedSubjectInput.value : "";
      const body = bodyInput.value.trim();

      if (!subject) {
        messageBox.textContent = "Please select a report reason.";
        messageBox.className = "report-modal-message error";
        return;
      }

      if (subject === "stealing content") {
        const selectedBeatId = worksSelect ? worksSelect.value : "";
        if (!selectedBeatId) {
          messageBox.textContent = "Please choose one of your beats.";
          messageBox.className = "report-modal-message error";
          return;
        }
      }

      submitBtn.disabled = true;
      submitBtn.textContent = "Submitting...";
      messageBox.textContent = "";
      messageBox.className = "report-modal-message";

      try {
        const payload = { subject };

        if (body) {
          payload.body = body;
        }

        if (subject === "stealing content") {
          const selectedBeatId = worksSelect ? worksSelect.value : "";
          if (selectedBeatId) {
            payload.user_beat_id = Number(selectedBeatId);
          }
        }

        const response = await fetch(`/report/${beatIdInput.value}`, {
          method: "POST",
          credentials: "include",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify(payload)
        });

        if (!response.ok) {
          if (response.status === 401) {
            showLoginPrompt();
            closeReportModal();
            return;
          }
          throw new Error("Report submission failed");
        }

        messageBox.textContent = "Thanks for reporting this beat.";
        messageBox.className = "report-modal-message success";
        this.reset();
        resetReportModalForm();
      } catch (error) {
        messageBox.textContent = "Could not submit the report. Please try again.";
        messageBox.className = "report-modal-message error";
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "Submit";
      }
    });

    modal.addEventListener("click", (event) => {
      if (event.target === modal) {
        closeReportModal();
      }
    });
  }

  const beatIdInput = document.getElementById("reportBeatId");
  const messageBox = document.getElementById("reportModalMessage");
  if (beatIdInput) {
    beatIdInput.value = beatId;
  }
  resetReportModalForm();
  if (messageBox) {
    messageBox.textContent = "";
    messageBox.className = "report-modal-message";
  }

  modal.classList.add("active");
}

function closeReportModal() {
  const modal = document.getElementById("reportModal");
  if (modal) {
    modal.classList.remove("active");
  }
}

function initializeBeatCardEvents(root = document) {
  attachProgressBar(root);
  attachPlayEvents(root);
  attachCartEvents(root);
  attachLikeEvents(root);
  attachSaveEvents(root);
  attachBeatMenuEvents(root);
}

function renderBeatCards(container, beats, emptyMessage = "No beats found.") {
  if (!container) return;

  if (!beats || !beats.length) {
    container.innerHTML = `<div class="empty-card">${emptyMessage}</div>`;
    return;
  }

  container.innerHTML = beats.map(createBeatCard).join("");
  initializeBeatCardEvents(container);
}

function showLoginPrompt() {
  let modal = document.getElementById("loginModal");
  
  if (!modal) {
    const modalHTML = `
      <div id="loginModal" class="login-modal-overlay">
        <div class="login-modal">
          <h2>Login Required</h2>
          <p>You need to login to perform this action.</p>
          <div class="login-modal-actions">
            <button class="login-modal-btn primary" id="loginModalLoginBtn">Login</button>
            <button class="login-modal-btn secondary" id="loginModalCancelBtn">Cancel</button>
          </div>
        </div>
      </div>
    `;
    
    document.body.insertAdjacentHTML("beforeend", modalHTML);
    modal = document.getElementById("loginModal");
    
    document.getElementById("loginModalLoginBtn").addEventListener("click", () => {
      window.location.href = "/login";
    });
    
    document.getElementById("loginModalCancelBtn").addEventListener("click", () => {
      closeLoginModal();
    });

    modal.addEventListener("click", (e) => {
      if (e.target === modal) {
        closeLoginModal();
      }
    });
  }
  
  modal.classList.add("active");
}

function closeLoginModal() {
  const modal = document.getElementById("loginModal");
  if (modal) {
    modal.classList.remove("active");
  }
}
