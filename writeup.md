# Week 8 — Agent Orchestration: The Recipe Box Sprint

## 1. Project Overview

The goal of this assignment was to extend the Recipe Box starter application using concurrent AI agents and a generator–critic workflow.

I used Visual Studio Code, GitHub Copilot, Git worktrees, Python, FastAPI, SQLite, and pytest.

The original starter application passed all three baseline tests before development began.

**GitHub Repository:** https://github.com/hacerdilarakivrak/recipe-box-week8

## 2. Part I — Concurrent Agents

### Selected Tasks

I selected two independent tasks from `docs/TASKS.md`.

| Agent | Task | Branch |
|---|---|---|
| Agent A | Shopping List | `task-a` |
| Agent B | Tag Filter | `task-b` |

Agent A implemented `GET /shopping-list?ids=1,2,3`, which merges ingredients from selected recipes into a deduplicated list.

Agent B implemented `GET /recipes?tag=breakfast`, which returns only recipes containing the requested tag while preserving the original behavior when no tag is provided.

### Git Worktree Setup

I created two separate Git worktrees from the same initial commit (`cffa503`).

```bash
git worktree add ../recipe-task-a -b task-a
git worktree add ../recipe-task-b -b task-b
git worktree list
```

Each worktree was opened in a separate VS Code window with its own GitHub Copilot agent session.

```text
starter/              → main
recipe-task-a/        → task-a
recipe-task-b/        → task-b
```

This allowed both agents to work independently without directly overwriting each other's files.

### Agent Instructions

Agent A received instructions to implement Shopping List, handle invalid and missing recipe IDs, add tests, and run the complete pytest suite. It was explicitly instructed not to implement Tag Filter.

Agent B received instructions to implement Tag Filter, preserve existing behavior, add tests, and run the complete pytest suite. It was explicitly instructed not to implement Shopping List.

Both agents were instructed to work only within their assigned worktree and were prohibited from switching branches, merging, committing, or pushing changes.

### Evidence of Concurrent Execution

I exported both agent sessions as JSON files:

- `agent-a-chat.json`
- `agent-b-chat.json`

The recorded tool execution timestamps provide evidence that the agents worked concurrently.

The following timestamps are from November 26, 2026, in Türkiye local time (UTC+3).

| Agent | First Recorded Tool Start | Last Recorded Tool Completion |
|---|---|---|
| Agent A | 16:00:49.499 | 16:01:35.953 |
| Agent B | 16:00:58.630 | 16:01:25.858 |

The recorded execution windows overlapped for **27.228 seconds**.

Additional evidence of simultaneous activity:

- Agent A started editing its project files at 16:00:59.017.
- Agent A completed that editing operation at 16:01:02.516.
- Agent B started reading its own project files at 16:01:01.523.

Therefore, Agent B was inspecting its worktree while Agent A was modifying files in a different worktree.

The original Unix timestamps for these operations were:

| Operation | Unix Timestamp (ms) |
|---|---:|
| Agent A first tool start | 1795698049499 |
| Agent A editing start | 1795698059017 |
| Agent A editing completion | 1795698062516 |
| Agent A last tool completion | 1795698095953 |
| Agent B first tool start | 1795698058630 |
| Agent B file inspection start | 1795698061523 |
| Agent B last tool completion | 1795698085858 |

These measurements represent recorded tool execution windows, not uninterrupted CPU usage.

### Results

Agent A reported:

> Invalid IDs return 422; missing recipes return 404.

Its implementation merged ingredients in order, removed duplicates, and included tests for invalid and missing recipe IDs.

Agent B implemented optional tag filtering and added tests to verify that matching recipes were included and nonmatching recipes were excluded.

| Test Stage | Result |
|---|---|
| Original starter | 3 passed |
| Agent A — Shopping List | 6 passed |
| Agent B — Tag Filter | 4 passed |
| Combined implementation | 7 passed |

After reviewing the changes and running the tests, I manually committed and pushed both branches.

I then integrated both tasks into the main branch:

```bash
git merge task-a --no-edit
git merge task-b --no-edit
python -m pytest
git push origin main
```

Relevant Git commits:

- `7682e19` — Implement shopping list feature with tests
- `9e65075` — Implement tag filter feature with tests
- `38f1768` — Merge branch 'task-b'

### Collisions and Risks

Both agents modified `main.py` and `test_main.py`, creating a potential merge-conflict risk.

However, separate Git worktrees prevented the agents from directly overwriting each other's working files. Both agents also had separate local database paths because each worktree contained its own project directory.

Git automatically merged the changes without requiring manual conflict resolution.

Worktree isolation reduced interference during development, but it did not eliminate the possibility of conflicts during integration. Running the combined test suite after merging was therefore essential.

## 3. Part II — Generator–Critic Workflow

### Selected Task

For the generator–critic workflow, I selected Ingredient Scaling.

The required endpoint was:

```text
GET /recipes/{id}/scaled?factor=2
```

For example, an ingredient containing `200 g flour` should become `400 g flour` when the scaling factor is 2.

I created a separate worktree after integrating the first two tasks:

```bash
git worktree add ../recipe-generator -b task-scaling
```

Two separate Copilot sessions were used in this worktree: a Generator agent and an independent Critic agent.

Unlike Part I, these agents worked sequentially so that each Critic review evaluated the latest Generator revision.

### Evaluation Rubric

The Critic evaluated the implementation using three criteria:

1. **Correctness:** Scaling calculations, decimal quantities, invalid factors, missing recipes, and boundary cases.
2. **Tests:** Test coverage, regression tests, and preservation of existing functionality.
3. **Clarity:** Code readability, maintainability, and documentation accuracy.

### Generator–Critic Transcript

The following transcript contains selected excerpts from the original exported conversations, together with summaries of the implementation changes. Local file paths and unrelated tool metadata have been omitted.

#### Stage 1 — Initial Generator Implementation

**Human prompt to Generator — excerpt:**

> Your task is to implement the Ingredient Scaling feature from docs/TASKS.md.

The Generator was instructed to implement the scaling endpoint, handle invalid factors and missing recipes, preserve Shopping List and Tag Filter, add tests, and run the complete pytest suite.

**Generator response — excerpt:**

> Implemented ingredient scaling via `GET /recipes/{id}/scaled?factor=2`. It scales leading integer or decimal quantities, preserves unquantified ingredients and the stored recipe, rejects invalid factors with 422, and returns 404 for missing recipes.

The Generator modified `main.py`, `test_main.py`, and `README.md`.

**Test result:** 10 passed.

#### Stage 2 — Critic Review Round 1

**Human prompt to Critic — excerpt:**

> Review the Generator's current Ingredient Scaling implementation in the task-scaling worktree.

The Critic was instructed to inspect the source code, Git diff, README, and tests using the correctness, tests, and clarity rubric without modifying project files.

**Critic findings:**

- Leading-decimal quantities such as `.5 cups milk` were not scaled correctly.
- Extremely large finite factors such as `1e999999` could cause a Decimal overflow and HTTP 500 response.
- Additional edge-case and regression tests were needed.

**Critic response — excerpt:**

> The core integer-and-decimal scaling behavior works, but the leading-decimal parsing gap and extreme finite-factor 500 are genuine correctness defects.

**Test result:** 10 passed.

**Verdict: NEEDS REVISION**

#### Stage 3 — Generator Revision Round 1

**Human prompt to Generator — excerpt:**

> 1. Fix leading-decimal quantity parsing.
> 2. Handle extreme finite scaling factors safely without returning HTTP 500.
> 3. Add regression tests for both identified defects.

The Generator was also instructed to preserve existing functionality, update documentation where necessary, and run the complete test suite.

**Generator response — excerpts:**

> Leading decimals: Updated quantity parsing to recognize values like `.5`; the regression test verifies `.5 cup sugar` scales to `1 cup sugar`.

> Unsafe inputs now return 422 rather than causing an HTTP 500. Added a regression test using `1e999999`.

**Changes made:**

- Improved the quantity parsing pattern.
- Added limits for scaling factors and result sizes.
- Added handling for Decimal arithmetic exceptions.
- Added regression tests.
- Updated endpoint documentation.

**Test result:** 11 passed.

**Git diff check:** Passed.

#### Stage 4 — Critic Review Round 2

**Human prompt to Critic — excerpt:**

> Verify that leading-decimal quantities are now handled correctly.

The Critic was also instructed to verify that extreme finite factors no longer caused HTTP 500 errors and to evaluate remaining correctness, test coverage, and clarity issues.

The Critic confirmed that both correctness defects identified in Round 1 had been fixed.

Manual API checks confirmed:

| Input | Result |
|---|---|
| `.5 cup sugar` × `2` | `1 cup sugar` |
| `.5 cup sugar` × `0.5` | `0.25 cup sugar` |
| `1e999999` | HTTP 422 |
| `1e-999999` | HTTP 422 |
| Missing factor | HTTP 422 |

However, the README still stated that only three tests should pass, and several boundary scenarios lacked explicit regression coverage.

**Critic response — excerpt:**

> The implementation fixes both correctness defects from Round 1 and is robust in the tested and manually probed boundaries. Revision is needed only for the stale README test count and the identified test-coverage gaps.

**Test result:** 11 passed.

**Verdict: NEEDS REVISION**

#### Stage 5 — Generator Revision Round 2

**Human prompt to Generator — excerpt:**

> 1. Update the outdated test count in README.md.
> 2. Add regression tests for extremely small scaling factors, such as 1e-999999.
> 3. Add a test for a missing scaling factor.
> 4. Review boundary cases and ensure appropriate HTTP 422 responses.

The Generator was instructed to preserve existing functionality and avoid unnecessary implementation changes.

**Generator revision summary:**

- Updated the README test count.
- Added regression coverage for extremely small scaling factors.
- Added coverage for a missing scaling factor.
- Added tests for supported result-size boundaries and oversized results.
- Preserved the existing implementation because further production-code changes were not necessary.

**Test result:** 13 passed.

**Git diff check:** Passed.

#### Stage 6 — Final Critic Review

**Human prompt to Critic — excerpt:**

> The Generator has completed two revision rounds based on your feedback.

The Critic was instructed to verify the final implementation, tests, documentation, boundary cases, and preservation of Shopping List and Tag Filter.

The Critic confirmed that:

- Leading-decimal quantities scaled correctly.
- Extreme and invalid factors returned HTTP 422.
- Missing factors returned an appropriate validation response.
- Boundary and overflow cases had regression coverage.
- Shopping List and Tag Filter remained intact.
- The README accurately reflected the implementation and test count.
- Stored recipes remained unchanged after scaling.

**Final Critic response:**

> The implementation satisfies the correctness, test coverage, and clarity requirements, with no remaining issues that justify revision.

**Test result:** 13 passed.

**Git diff check:** Passed.

**Final Verdict: APPROVED**

### Revision Summary

| Stage | Tests Passed | Critic Verdict |
|---|---:|---|
| Initial implementation | 10 | Needs Revision |
| Revision Round 1 | 11 | Needs Revision |
| Revision Round 2 | 13 | Approved |

The workflow completed two actual revision rounds before receiving final approval.

### Final Integration

After the Critic approved the implementation, I manually reviewed the changes, ran the tests, committed the implementation, and pushed the `task-scaling` branch.

I then merged the completed feature into the main branch.

```bash
git merge task-scaling --no-edit
python -m pytest
git push origin main
```

Final implementation commit:

`296ad79` — Implement ingredient scaling with two generator-critic revision rounds

## 4. Agent Autonomy and Human Supervision

I used controlled autonomy throughout the assignment. Agents were allowed to perform their assigned tasks independently, but repository-level decisions remained under human control.

| Agent | Autonomy Level | Allowed Actions | Restricted Actions |
|---|---|---|---|
| Agent A | Supervised implementation | Read files, edit Shopping List code, add tests, run local tests | Modify the other worktree, commit, push, merge, switch branches |
| Agent B | Supervised implementation | Read files, edit Tag Filter code, add tests, run local tests | Modify the other worktree, commit, push, merge, switch branches |
| Generator | Supervised implementation and revision | Implement Ingredient Scaling, revise code, add tests, update documentation | Commit, push, merge, switch branches |
| Critic | Read-only review | Inspect code, inspect diffs, run tests, report issues and recommendations | Modify project source files, commit, push, merge, switch branches |

I supervised the agents by defining their task boundaries, reviewing proposed changes, and approving terminal operations when required.

I manually transferred the Critic's feedback to the Generator after each review round. The Critic was not allowed to fix the implementation directly.

I retained responsibility for Git commits, branch integration, pushing changes to GitHub, and final verification.

## 5. Final Project Results

The final application contains three new features:

- Shopping List
- Tag Filter
- Ingredient Scaling

All three features are integrated into the main branch.

The final test suite contains 13 passing tests.

One existing FastAPI/Starlette test-client deprecation warning remains. It does not cause any test failures.

The original agent conversation exports were retained as supporting evidence:

- `agent-a-chat.json`
- `agent-b-chat.json`
- `generator-chat.json`
- `chat.json` — Critic conversation

The relevant timestamps and transcript excerpts are included in this writeup.

## 6. What I Learned

I learned that running independent agents concurrently can improve development efficiency when their responsibilities are clearly separated. Git worktrees helped prevent agents from overwriting each other's changes, although integration still required careful review and testing. The generator–critic workflow demonstrated that passing tests alone does not guarantee correctness, because an independent reviewer can identify important edge cases. I also learned that limiting agent autonomy and maintaining human control over Git operations makes multi-agent development safer and more manageable.