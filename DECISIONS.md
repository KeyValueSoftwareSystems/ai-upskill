# Decisions

One line each, in your own words. The room compares them after the build.

## 1. Should the agent write and run code at all, or should LaunchKit get one tool per calculation? What does each cost?

## 2. Where should the agent's code run: a container you start yourself, a sandbox server such as OpenSandbox, a micro-VM, or a hosted sandbox? What does your answer cost?

## 3. One sandbox per run, per conversation, or per brand? What does each keep between runs, and what can leak between them?

## 4. Which limits does a run need, and what number did you pick for each? Which ones belong to each request, and which to the sandbox server? Which would you lower first with forty brands on one machine?

## 5. A message arrives while a job runs: wait, refuse, or stop the job? Who owns the job once the page is gone?

## 6. After a restart, what does "carries on" mean, and which steps must never happen twice? When would you take a durable-execution engine instead?

## 7. Why the scripted models: what does the room lose by not watching the real model make these mistakes, and what does it gain?
