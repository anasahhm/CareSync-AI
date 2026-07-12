# Demo Script (click-by-click)

Prerequisite: backend + frontend running (see `RUNBOOK.md` §1-2), or the full Docker stack up.

1. Open `http://localhost:3000`. Click **Get Started** → **Register** → create a **Doctor** account, then in a second (private/incognito) browser window, register a **Patient** account.
2. As the Patient: **Dashboard → New Consultation**, enter chief complaint e.g. *"Sharp abdominal pain for 2 days, feels worse when I press on it"*, submit.
3. As the Doctor: **Dashboard → Waiting Room**, click the new consultation to join → you're now both in `ConsultationRoom`.
4. Click **Start** on the **Vision Observations** panel (bottom-left, doctor view only) → grant camera permission. Sit back slightly and make a pained expression / hold your side — within ~1.5s the panel should populate `pain_score`, `emotion`, `posture`.
5. As the Doctor, use the annotation tool (pencil icon) to tap the abdomen area on the patient's video feed — this becomes a `body_region`-tagged annotation the Symptom Agent can read.
6. Click **Generate Report** (or the equivalent action that calls `POST /api/agents/process/{id}`) — this triggers the full 17-agent run.
7. Click **View Report** → the **AI Consultation Report** modal opens with `ReportViewer`.
8. Scroll down (doctor-only) to **Agent Insights (Doctor View)**:
   - **Consensus Timeline tab**: watch/point out the batch-ordered event list (agent_started → agent_completed → recommendation_available → escalation_required → moderator_decision → consensus_update), and the Final Consensus card at top (primary diagnosis, consensus %, risk badge, agents agreed/total).
   - **Memory tab**: show the conversation turns, the per-agent output badges, and the shared-facts list (e.g. `symptom_top_recommendation`).
   - **RAG Explorer tab**: type a query like *"acute appendicitis abdominal pain"*, click search, show the hybrid score bars and citations.
9. Back in the report itself, click the **PDF**, **Markdown**, and **JSON** export buttons in turn — each should show a loading spinner, then a success toast, then trigger a real file download.
10. Switch to the Doctor Dashboard's right sidebar → **GPU Dashboard** card — point out the detected backend (CPU in a laptop demo; ROCm if running on the AMD-provisioned box) and health status.
11. (Optional, if time allows) Open the **AI Reports** list on the Doctor Dashboard, click a past report to reopen the same modal for a second, already-completed consultation — demonstrates the timeline/memory/RAG tabs work for historical data too, not just the live run.

## If something doesn't show data

- **Vision panel stays empty**: check browser camera permission was actually granted; check backend log for `mediapipe` import errors (see `RUNBOOK.md` §4 for the `mp.solutions` version check).
- **RAG Explorer returns nothing**: the seeded guideline corpus is small and topic-specific (cardiac, respiratory, GI, neuro, dermatologic, musculoskeletal, fever, pain) — try a query matching one of those categories, e.g. *"asthma bronchodilator"*.
- **Consensus Timeline is empty**: confirm step 6 (process/generate) was actually triggered — the timeline only populates after a processing run.
- **GPU Dashboard shows CPU**: correct and expected on a non-GPU machine — say so directly, it's a fallback demonstration, not a bug.
