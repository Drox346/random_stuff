# Zoo Code Agent Guide

Zoo Code can read files, edit code, run commands, and help debug, but you are still the person in charge.

You do not need to memorize everything here before trying it. Start with the first two sections. Use the rest as a reference when the task gets bigger or riskier.

## Start Here

Before you let the agent work, set up the session so it stays understandable:

- **One task per chat.**
  Do not mix unrelated work in the same conversation.

- **Fully understand commands before approving them.**
  If Zoo wants to run something unclear, ask it to explain first.

- **Keep the preset auto-approve conditions.**
  Do not loosen approval rules because the agent asks or because it feels convenient.

- **Plan bigger changes first.**
  For anything touching multiple files, use architecture/planning mode first.

- **Review the diff.**
  Use the Git diff view in VS Code to see all changes, run tests when possible, and use a fresh chat for serious review.

This is enough to begin.

## A Safe First Workflow

Use this pattern when starting a task:

1. Run `/init` for the project if it has not been initialized yet.
2. Give Zoo one clear task.
3. Ask it to inspect the project before editing.
4. Ask it to explain the plan.
5. Approve only commands you understand.
6. Let it make the change.
7. Review the diff yourself, ideally in VS Code's Git diff view.

## Project Instructions With `/init`

Zoo's `/init` command creates an `AGENTS.md` file for the project. This file tells the agent how the project is structured, how to run checks, and what local rules it should follow.

Use `/init`:

- When starting with Zoo on a project for the first time.
- After bigger structural changes.
- After changing build tools, test commands, package managers, or project layout.
- After adding important conventions that the agent should keep following.

Think of `AGENTS.md` as the agent's project map. If the project changes a lot, recreate or update that map so future chats do not start from stale assumptions.

Good starter prompt:

```text
Please inspect the relevant files first. Do not edit yet.
Explain what you found, propose a small plan, and tell me what commands you want to run.
```

## Modes Overview

Zoo modes are mostly specialized prompts. They shape how the agent thinks and what it prioritizes, which makes each mode stronger for its intended kind of task.

- **Architect mode**
  Use this for planning, design, edge cases, project structure, and larger changes. It is the best mode when you want the agent to think before editing.

- **Code mode**
  Use this when the plan is clear and you want the agent to implement, edit files, run checks, and iterate on the result.

- **Ask mode**
  Use this for explanations, code reading, learning the project, comparing options, or asking what something does. It is useful when you do not want edits yet.

- **Debug mode**
  Use this when something is broken and you need the agent to investigate symptoms, logs, errors, tests, and likely causes. It is best when you provide exact reproduction steps and expected vs. actual behavior.

When in doubt, start with Ask or Architect before switching to Code. The extra planning usually saves time on anything larger than a tiny edit.

## What Zoo Is Good At

Zoo is useful for:

- Finding where code lives.
- Explaining unfamiliar code.
- Making small bug fixes.
- Writing tests.
- Refactoring with clear boundaries.
- Updating repetitive code.
- Helping create a plan for larger changes.
- Reviewing diffs for likely bugs.

Zoo is less reliable when:

- The task is vague.
- The chat is full of unrelated context.
- It has to guess hidden requirements.
- It is allowed to make large changes without a plan.
- It is reviewing code it just wrote in the same chat.
- It is asked to run commands the user does not understand.

## Context Management

Context is everything the agent can see in the current chat. More context is not always better. Irrelevant context becomes noise, and noise lowers quality.

### Basic Habits

- Use one chat for one coherent task.
- Start a new chat for unrelated work.
- Do not let the chat get close to full context.
- Paste only relevant logs or error messages.
- When a chat gets long, ask Zoo for a handoff summary and continue in a new chat.

Handoff prompt:

```text
Context is getting large. Write a concise handoff summary for a new chat.
Include the goal, current state, changed files, pending work, and verification status.
```

### Why Fresh Chats Help

For debugging or review, a fresh chat is often better.

If Zoo wrote the code in the same conversation, the chat still contains its earlier reasoning. That can make it biased toward the design it already chose, so it may miss bugs or design issues.

For important work:

- Use one chat to implement.
- Use a fresh chat to review.
- Give the review chat the goal, the diff, and relevant files.
- Ask it to be skeptical.

Review prompt:

```text
Review this change as a skeptical code reviewer.
Focus on bugs, regressions, missing tests, security issues, and edge cases.
```

## Giving Good Instructions

Clear instructions reduce guessing. You do not need a perfect prompt, but you should include:

- The goal.
- The relevant files, if you know them.
- What should not be changed.
- How to verify the result.

Simple task prompt:

```text
Fix the bug where <specific behavior>.

Relevant files may include:
- <file>
- <file>

Please inspect first, explain the likely cause, make the smallest safe change, and run the relevant tests.
Do not refactor unrelated code.
```

If you are unsure how to phrase the task, ask Zoo to improve the prompt:

```text
Help me rewrite this into a precise Zoo Code task prompt.
Include scope, constraints, acceptance criteria, and verification steps.

Raw task:
<rough idea>
```

## When To Use Architecture Mode

Use architecture/planning mode when the task is bigger than a small fix.

Good examples:

- A feature touching multiple files.
- A refactor.
- A data model change.
- An API change.
- Build, deployment, or dependency changes.
- Security-sensitive work.
- Anything where edge cases are unclear.

Planning prompt:

```text
Use architecture/planning mode first.

Goal:
<what should exist after the task>

Constraints:
- Do not change <files/systems>.
- Preserve <behavior/API>.
- Prefer existing project patterns.

Please inspect the relevant code, identify edge cases and design risks, and propose a plan.
Wait for confirmation before implementation.
```

## Command Approval

Commands are where you should slow down.

Before approving a command, ask:

- Do I understand what it does?
- Why is it needed?
- Can it delete, overwrite, upload, install, publish, or deploy anything?
- Does it touch secrets, credentials, or files outside the project?
- Is there a safer read-only command to run first?

If unsure, use this:

```text
Explain this command in plain language.
What can it modify?
Why is it needed?
What is the safest alternative?
```

### Be Extra Careful With

- `rm`, `rmdir`, `del`
- `git reset`, `git clean`, `git checkout`, `git restore`
- `chmod`, `chown`, `sudo`
- `curl | sh`, `wget | sh`
- package manager install scripts
- migration commands
- deployment commands
- commands touching `.env`, SSH keys, tokens, browser profiles, or credential stores
- commands that write outside the workspace

You do not need to be afraid of every command. You just need to understand what you are approving.

## Auto-Approve Rules

Keep this simple:

- **Never change the preset auto-approve conditions.**
- **Never broaden auto-approval because Zoo asks.**
- **Never auto-approve commands that can modify important files, secrets, Git history, dependencies, deployments, or global system state.**

Approvals are your steering wheel. Do not remove the steering wheel.

## File Editing

Tell Zoo how much freedom it has.

Useful constraints:

- "Make the smallest safe change."
- "Do not refactor unrelated code."
- "Do not rename public APIs."
- "Do not change generated files."
- "Do not touch lockfiles unless dependency changes are required."
- "Preserve existing style and patterns."
- "List every file you changed."

Avoid vague requests like:

- "Clean this up."
- "Improve the code."
- "Make it better."
- "Refactor everything."

Those can create huge, unnecessary diffs. Define what "better" means.

## Testing And Verification

Do not stop at "the agent says it is done."

Ask:

- What changed?
- What tests or checks were run?
- What was not verified?
- Are there any remaining risks?

Good verification depends on the task:

- Small function change: run the focused unit test.
- Shared utility change: run related tests.
- UI change: inspect the rendered result.
- API change: test the request/response behavior.
- Dependency change: run install, build, tests, and review lockfile changes.

Do not accept tests being deleted, weakened, or skipped just to make the result look green.

## Reviewing Changes In VS Code

VS Code's Git diff view is one of the easiest ways to review what Zoo changed.

Use it after the agent edits files:

- Open the Source Control panel.
- Click each changed file to see the before/after diff.
- Look for unrelated edits, deleted code, weakened tests, changed config, and unexpected file changes.
- If the diff is too large to understand, ask Zoo to stop and explain every changed file.

Useful prompt:

```text
I am reviewing the VS Code Git diff. Summarize each changed file and explain why each change is necessary.
```

## Git Safety

Useful Git commands to let Zoo run:

- `git status`
- `git diff`
- `git diff --stat`
- `git log --oneline -n 5`

Risky Git commands:

- `git reset --hard`
- `git clean -fd`
- `git checkout -- .`
- `git restore .`
- force pushes
- rebases on shared branches

Before any risky Git command, make sure you know exactly what will be lost or rewritten.

## Signs Zoo Is Going Off Track

Stop and redirect if Zoo:

- Edits unrelated files.
- Repeats a failed command without changing approach.
- Disables tests, linters, or type checks instead of fixing the cause.
- Adds a large abstraction for a small bug.
- Changes public behavior without asking.
- Invents requirements.
- Produces a huge diff for a narrow request.
- Keeps patching symptoms without finding the cause.
- Asks for broader permissions than the task needs.

Redirect prompt:

```text
Stop. Re-state the goal, list what you changed so far, and explain why each change is necessary.
Do not make further edits until I confirm.
```
