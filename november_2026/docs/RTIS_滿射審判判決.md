# 【11 月版本】RTIS 滿射提案的審判紀錄（court 技能，2026-11-15）

判決：**有罪，10 比 2**。中文摘要見 `claude/RTIS_遺傳與幾何企劃.md` 第十六節。以下是審判的原始紀錄（英文，工具輸出）。
陪審員只看得到案件檔，看不到對話；這是工具的輸出，不是事實認定。

---

## Case file 案件檔

Make RTIS inheritance surjective ("讓組合可以滿射，也就是讓所有遺傳組合都可能出現") by adding one linkage map per part plus a separate mutation step, built behind a switch that is off by default.

## Background on the project

- RTIS is the user's AI-driven cross-species creature generation system. The user is an undergraduate (computer and communication engineering, Taiwan) aiming at an IEEE CoG 2026 paper.
- Project rule: work is split into A-zone (needed for the paper) and B-zone (future work). The paper's claim is PCE, a part-correspondence engine that matches parts of two parent species by semantic tags. All of the geometry and inheritance work described below is B-zone; none of it is required for the paper.
- Project rule: a task is not "done" until it has run on the user's own machine with Python 3.10.12. So far all of this work has run only in a cloud workspace (Python 3.10.12 there), not on the user's machine.

## How inheritance works today (all built and tested in prototypes)

- Each creature is a tree of parts; each part is a chain of bones. Genes: one vector per bone (length and direction), one thickness per joint, plus a few per-part genes (skin blend, attach point, cross-section outline).
- Two parents' parts are matched by PCE tag similarity: score >= 0.40 always matched, 0.25 to 0.40 matched by chance ((score - 0.25) / 0.15), below 0.25 never.
- Each gene is copied whole from one parent, never averaged.
- Linkage: along a part's chain, genes travel in runs with exactly one switch point per part.
- A "part-attribute layer" (off by default) measures each long part as length, thickness, taper and bend, and inherits each attribute whole from either parent. Repeated parts with the same tags (e.g. a spider's four leg pairs) form a "limb set": count and placement come from one parent, attributes from either.
- Unmatched parts are kept by chance; two unmatched limbs in the same place compete and only one stays.

## Measured results so far (cloud runs)

- Linkage test, 45 children per variant (15 parent pairs x 3 children): children whose body developed extra "beads" (a body that looks like a string of balls): fully independent genes 24/45, thickness stored as ratios 16/45, one switch point per part 4/45, two switch points per part 11/45, whole thickness profile from one parent 0/45. One switch point per part was adopted.
- Attribute layer on vs off, 15 parent pairs x 6 seeds (90 children each): children with a hidden part 16/90 off vs 4/90 on; all bodies one closed mesh in both; other measures unchanged.
- Biped x spider legs with the attribute layer, 300 matings: 2 legs 55%, 8 legs 45%; each "pure" outcome (e.g. 8 legs all spider-like) 9% to 13%; mixed outcomes 23% and 30%. A product formula (each choice's probability multiplied) predicts 12.5% and 25%.

## The problem the user raised

The user asked how to make the combinations surjective: every inheritance combination should be able to appear, instead of only the combinations someone wrote a rule for. Reasons some children are impossible today:
1. Locks: count and placement are locked together; a limb set makes one choice for all its limbs; only one switch point per part.
2. Parts scoring below 0.25 never match, so they never trade anything (e.g. a leg and a jellyfish tentacle score 0.14).
3. Round parts, the main body and long x round pairs are skipped by the attribute layer.

## The proposal on trial

Two mechanisms together, both behind a switch that is off by default so current results stay unchanged:

1. **One linkage map per part.** All of a part's traits sit in one row. Walking along it, the source parent switches between neighbouring traits with a probability r set per neighbour pair: 0 = locked together, small (e.g. 0.05) = usually together, 0.5 = independent. Today's rules become special cases (attributes 0.5, count-placement 0, bones small). Surjectivity = no r is 0. The probability of a given pattern = 1/2 x product over neighbour pairs of (r if the source switches, 1 - r if not). If the rarest child has probability p, about 3/p matings are needed to see it with 95% certainty.
2. **A mutation step** for changes that are not combinations of the two parents: a limb borrowing one attribute (e.g. length or ring arrangement) from an unmatched part of the other parent, and new counts (4 or 6 legs from parents with 2 and 8). RTIS already has a mutation step with a budget.

Alternatives that were considered and set aside: giving each lock its own small probability (one setting per rule, more for every new rule); making everything independent and filtering bad bodies afterwards (would discard over half, given 24/45 beaded bodies).

## Known gaps stated with the proposal

- Not tested. The map allows two or more switch points in a part, and two switch points gave 11/45 beaded bodies, so the per-neighbour values would need tuning against that test.
- It does not cover round parts or the main body (needs a long x round rule still on the to-do list).
- The probability formula covers gene choices, not whether bodies look good; the "two limbs compete for one place" rule depends on shapes and must be counted by running matings.
- The user has not decided how rare "rare" should be (5% was suggested).

---

## Prosecution opening 檢方開場

Opening: Prosecution

**1. It does not deliver the surjectivity it promises.** The goal is "every inheritance combination should be able to appear." The case lists three causes of impossible children. The map only removes the locks in cause 1. Cause 3 stays: "It does not cover round parts or the main body." Cause 2 (parts below 0.25 "never trade anything") is passed to a mutation step that "already has... a budget," which makes those children capped mutations, not inheritance. Cost: the feature ships under a claim it does not meet.

**2. It turns back on the failure the project measured and rejected.** "One switch point per part was adopted" because it gave 4/45 beaded bodies. The map "allows two or more switch points," and "two switch points gave 11/45." Surjectivity requires "no r is 0," so count and placement, now locked at 0, must come apart too. Cost: body quality falls back toward the variants that were thrown out, and "tuning" has no target yet.

**3. Making it safe makes it useless.** To limit damage, r must be small, but by the case's own formula a child needing one switch at r = 0.05 has p ≤ 1/2 x 0.05 = 2.5% (about 120 matings to see it), and two such switches give 0.125% (about 2,400). Both are below the suggested 5% "rare" line. Cost: combinations that are possible on paper but never seen in practice.

**4. The probability math is not a guarantee.** The product formula already missed: it "predicts 12.5% and 25%" against measured "9% to 13%" and "23% and 30%." The case admits the compete rule "must be counted by running matings." Cost: no design-time proof that any given child can actually appear.

**5. Wrong priority and no definition of done.** "All of the geometry and inheritance work... is B-zone; none of it is required for the paper." It is "Not tested," has never run on the user's machine (the project's own bar for "done"), and "the user has not decided how rare 'rare' should be." Cost: time taken from the IEEE CoG 2026 paper for work with no acceptance test.

**Missing from the record:** the number of neighbour pairs per row and the planned r values. Without them nobody can work out the rarest child's p, so the matings needed cannot be estimated.

---

## Defense opening 辯方開場

Opening: Defense

1. **It costs the paper nothing and changes no result.** The record says it is built "behind a switch that is off by default so current results stay unchanged," and that all of this is "B-zone; none of it is required for the paper." The obvious objection is that it pulls time away from the paper. The answer is that nothing in the PCE claim depends on it, so going ahead puts nothing A-zone at risk.

2. **One mechanism replaces a growing pile of rules.** "Today's rules become special cases (attributes 0.5, count-placement 0, bones small)," and "Surjectivity = no r is 0," a condition anyone can check. The set-aside alternative needs "one setting per rule, more for every new rule." One setting per neighbour pair gives the user one place to tune, not a new lock for every new rule.

3. **The maths already matches measured data.** For biped x spider, "A product formula ... predicts 12.5% and 25%," against measured "9% to 13%" pure outcomes and "mixed outcomes 23% and 30%." The map's probability is the same kind of product, and "about 3/p matings" turns that into a test budget. The objection is that the formula ignores whether bodies look good. The record admits this, and the stated fix is to count by running matings.

4. **The cheaper alternative fails on the evidence.** With "fully independent genes," 24/45 children grew beads, so filtering afterwards "would discard over half." The map can set small r on bones and stay close to the adopted one-switch-point setting (4/45). Two switch points gave 11/45, but a small r makes a second switch rare, and the record already lists "tuning against that test."

5. **The mutation step reuses what exists.** Counts such as "4 or 6 legs from parents with 2 and 8" cannot come from mixing two parents at all, and "RTIS already has a mutation step with a budget."

**Concessions:**
- "Not tested" anywhere, and never run on the user's machine, so it is not "done" under the project's rule.
- It does not cover "round parts or the main body," so the goal that "all combinations" can appear is met for long parts only.
- The pairs scoring below 0.25 are handled only partly, through mutation.
- How rare "rare" should be is still undecided.

---

## Prosecution rebuttal 檢方反駁

Rebuttal: Prosecution

1. **Partly survives.** The off switch protects current results. But "costs nothing" is unshown: the record is silent on time left before the paper and on build effort, so the cost is unknown, not zero.

2. **Partly survives.** Folding today's rules into one form is real. But settings still grow with every neighbour pair added, and surjectivity requires moving count-placement off 0, which no run has tested.

3. **Fails.** The 12.5% / 25% match comes from the attribute layer, not the map, which has never run. Mixed outcomes (23%, 30%) already stray from 25%, and the "compete for one place" rule sits outside the formula. With no rarest p given, "3/p matings" sets no actual budget.

4. **Partly survives.** Filtering afterwards does fail (24/45). But the defense's answer works against the goal. Surjectivity needs every r above 0, so parts can get two or more switch points, and the only evidence there is 11/45 beaded bodies. A small r lowers beads only by making the target combinations rare.

5. **Partly survives.** A budgeted mutation step exists, but the record does not say it can borrow attributes from unmatched parts or create new leg counts. Mutation also produces non-combinations, so it cannot make "all combinations" appear.

**The point to decide:** point 4. Nothing in the record shows that every r above 0 can coexist with a low bead rate. The only data (11/45 at two switch points) points the other way, and the proposal is untested.

---

## Defense rebuttal 辯方反駁

Rebuttal: Defense

**1. Partly survives.** Round parts and the main body are left out (conceded). That calls for a narrower claim ("surjective for long parts"), not for stopping. The record never says the mutation budget blocks the below-0.25 trades.

**2. Partly survives.** The map allows extra switch points but does not force them. With small r on bones, a second switch stays rare, so the 11/45 variant does not come back. What survives: count and placement must come apart, and tuning has no target yet.

**3. Fails.** The goal is that every combination "can appear." Today those children have p = 0. At 0.125% they are rare, not impossible. The 5% line was only "suggested." Runs of 300 matings already exist, so thousands is feasible.

**4. Fails as a reason to stop.** "No r is 0" makes every pattern possible by construction. The formula only sizes the test, and it landed within a few points of what was measured. The compete rule is a real gap, with a stated fix: count by running matings.

**5. Partly survives.** It is off by default and in the B-zone, so the paper is not at risk. "Not tested" holds for any unbuilt proposal. The missing acceptance test survives; fixing a rarity threshold supplies one.

**Decide on point 2:** can a map with no r at 0 keep beaded bodies near 4/45? The record has no pair counts or r values, so only a test can answer. The off switch makes testing free.

---

## Jurors 陪審員

### 1. The Accountant

VOTE: GUILTY

REASON: I won't sign off on spending the user's time, taken from the A-zone paper, on a B-zone feature whose bill nobody can work out: the record gives no build effort, no time left before the paper, and no r values or neighbour-pair counts, so the "about 3/p matings" test budget has no number in it, and what that unknown cost buys falls short of the "every combination" promise (long parts only, and the below-0.25 pairs pushed onto a budget-capped mutation step).

DECIDING FACT: The record does not give the number of neighbour pairs per row or the planned r values, so nobody can work out the rarest child's p or the matings needed to see it, and the only rough figure (one switch at r = 0.05 gives 2.5%, two give 0.125%, about 2,400 matings) is already below the suggested 5% "rare" line.

WOULD FLIP IF: The proposal came with planned r values and pair counts that give a rarest-child p and a matings count that fit a stated time budget the user can spend without delaying the IEEE CoG 2026 paper, with the claim narrowed to "surjective for long parts."

### 2. The First-Time Customer

VOTE: GUILTY

REASON: As a first-timer I would not buy something sold as "every inheritance combination can appear" when its own spec says it leaves out round parts and the main body, sends the below-0.25 pairs to a budgeted mutation step instead of inheritance, and has never run once, so what it promises and what it does don't match.

DECIDING FACT: The case's own known gaps say "It does not cover round parts or the main body," and the defense concedes the goal "is met for long parts only."

WOULD FLIP IF: The proposal were restated as "surjective for long parts only, off by default," so the claim matched what it actually covers.

### 3. The Competitor

VOTE: GUILTY

REASON: As the rival I would ignore this, since a per-neighbour switch probability is textbook recombination I could copy in a day, and what I would fear from them is the PCE paper; as described, the map buys "surjectivity" at the risk of bringing back the beaded bodies they already threw out, with no run showing otherwise.

DECIDING FACT: The map "allows two or more switch points in a part, and two switch points gave 11/45 beaded bodies", against 4/45 for the one-switch rule that was adopted, and surjectivity requires every r above 0.

WOULD FLIP IF: A run (even in the cloud) showed the map with no r at 0, count-placement included, keeping beaded bodies near 4/45 while the target combinations still turned up at a stated, agreed rarity line.

### 4. The Retired Judge

VOTE: GUILTY

REASON: The proposal is described as making all inheritance combinations possible, but the record admits it does not do that, and the defense itself asks for a narrower claim; a proposal that stands only after its own headline is cut back has failed as stated, whatever the off switch protects.

DECIDING FACT: The case's own "Known gaps" say "It does not cover round parts or the main body," and the defense's rebuttal concedes this "calls for a narrower claim ('surjective for long parts')."

WOULD FLIP IF: The proposal were restated as an experiment on long parts only, still behind the off switch, with an acceptance test fixed before building: a chosen rarity threshold and a beaded-body rate it must stay at or below, judged against the adopted 4/45.

### 5. The Teenager

VOTE: GUILTY

REASON: It's sold as "every combo can show up," but the weird ones people would actually screenshot, like a leg crossed with a jellyfish tentacle or anything on the round parts and main body, are left out or pushed to mutation, and the rest at a safe r are so rare that nobody will ever see them.

DECIDING FACT: By the case's own formula, a child that needs two switches at r = 0.05 has p = 0.125%, roughly 2,400 matings to see it once, which is far below the 5% "rare" line that was suggested.

WOULD FLIP IF: A real run showed the newly possible children showing up near the suggested 5% while beaded bodies stayed close to the adopted 4/45.

### 6. The Engineer

VOTE: NOT GUILTY

REASON: This can be built and it fails safely: it sits behind a switch that is off by default, the first thing likely to break (beaded bodies when every r is above 0) can be measured with a test the project already has, and the overstated "all combinations" claim means the label should be narrowed to long parts, not that the build should stop.

DECIDING FACT: The linkage test already exists (15 parent pairs x 3 children, with a 4/45 bead baseline for one switch point and 11/45 for two), and the map's settings have never been run against it. So whether small r keeps beads low is an open question that a cheap test can settle, not a failure already shown.

WOULD FLIP IF: The map were switched on by default or replaced the current one-switch-point rule before that bead test was run, because then the 11/45 result points to an untested change spoiling results the project already measured and adopted.

### 7. The Small-Business Owner

VOTE: GUILTY

REASON: The paper is the only thing that pays here, and this is spare-room work with nobody asking for it, no finish line ("rare" undecided, bead target unset) and a promise of "all combinations" it already admits it won't keep, so I wouldn't put Monday morning's hours into it as described.

DECIDING FACT: "All of the geometry and inheritance work described below is B-zone; none of it is required for the paper," and it is "Not tested," with no acceptance target set.

WOULD FLIP IF: The record showed the A-zone PCE paper work done or on schedule with time to spare, so this would run only in slack hours instead of eating time the paper needs.

### 8. The Statistician

VOTE: NOT GUILTY

REASON: The only evidence against the map is 11 beaded bodies out of 45 children, a tiny sample from a variant that forced two switch points into every part, while a small r would only rarely give a part a second switch, so the expected bead rate sits close to the adopted 4/45 and nothing in the record shows the plan fails; behind an off switch, a test is the right next step.

DECIDING FACT: The linkage test used only 45 children per variant (15 parent pairs x 3 children), and the 11/45 figure measured parts that always had two switch points, not parts that get a second switch with a small probability.

WOULD FLIP IF: The record gave the neighbour-pair counts and planned r values, and they showed that the rarest long-part child needs far more matings than can be run (well beyond the 300-mating runs that exist), so the "possible" combinations would never actually be observed or checked.

### 9. The Parent

VOTE: GUILTY

REASON: I would not let my own kid spend scarce time before a paper deadline on B-zone work that promises "all combinations" when its own defenders admit it only covers long parts, has never been tested, and has no finish line.

DECIDING FACT: The defense concedes that it does not cover "round parts or the main body," so the goal that "all combinations" can appear "is met for long parts only," which means the proposal fails as described.

WOULD FLIP IF: The case were restated as a small, time-boxed experiment for long parts only, with a fixed rarity threshold and a pass bar for beaded bodies near the adopted 4/45, so it has a clear stopping point and an honest claim.

### 10. The Investor

VOTE: GUILTY

REASON: I would not put my money into this as described, because the payoff is B-zone work the paper does not need, the headline promise of "all combinations" is already conceded to cover only long parts, and the only data on more switch points (11/45 beaded bodies against the adopted 4/45) points to losses, with no pass/fail bar to tell me when to stop paying.

DECIDING FACT: The proposal is "Not tested", and the record gives no neighbour-pair counts, no planned r values and no chosen rarity threshold ("5% was suggested"), so neither the cost nor the success condition can be worked out.

WOULD FLIP IF: The proposal were rescoped as a time-boxed experiment on long parts only, run after the A-zone paper work, with a stated pass bar set before building: beaded bodies near 4/45 with every r above 0, and the rarest child above the chosen rarity threshold.

### 11. The Designer

VOTE: GUILTY

REASON: A stranger reading the headline would believe "every inheritance combination can appear," but the defense itself concedes the label must shrink to "surjective for long parts," with mutation covering the rest, so the plan as described promises something its own design does not deliver.

DECIDING FACT: The proposal's stated gap that "it does not cover round parts or the main body," together with the defense's rebuttal that this "calls for a narrower claim ('surjective for long parts')."

WOULD FLIP IF: The case were restated as "surjective for long parts only, behind an off switch," with the per-neighbour r values and the rarity threshold written down, so the headline and the actual scope matched.

### 12. The Lawyer

VOTE: GUILTY

REASON: I find no legal or regulatory trap in the record, and the off-by-default switch keeps the liability inside B-zone. But read as a promise, the proposal says "all inheritance combinations can appear" and its own known gaps say it does not, so it should not go ahead under that claim.

DECIDING FACT: The case's own known gaps say "It does not cover round parts or the main body," and the defense concedes the goal "is met for long parts only," so the stated claim is untrue on its face.

WOULD FLIP IF: The case narrowed its claim to "surjective for long-part gene combinations" and set a rarity threshold as its acceptance test, so that what it promises matches what it delivers.

---

## Verdict 判決

The verdict: GUILTY, 10 to 2

**The case:** Make RTIS inheritance surjective ("讓組合可以滿射，也就是讓所有遺傳組合都可能出現") by adding one linkage map per part plus a separate mutation step, built behind a switch that is off by default.

**The charge:** The case fails as stated: it should not go ahead the way it is described.

### How the jury voted

| Juror | Vote | Why |
|---|---|---|
| The Accountant | GUILTY | I won't sign off on spending the user's time, taken from the A-zone paper, on a B-zone feature whose bill nobody can work out: the record gives no build effort, no time left before the paper, and no r values or neighbour-pair counts, so the "about 3/p matings" test budget has no number in it, and what that unknown cost buys falls short of the "every combination" promise (long parts only, and the below-0.25 pairs pushed onto a budget-capped mutation step). |
| The First-Time Customer | GUILTY | As a first-timer I would not buy something sold as "every inheritance combination can appear" when its own spec says it leaves out round parts and the main body, sends the below-0.25 pairs to a budgeted mutation step instead of inheritance, and has never run once, so what it promises and what it does don't match. |
| The Competitor | GUILTY | As the rival I would ignore this, since a per-neighbour switch probability is textbook recombination I could copy in a day, and what I would fear from them is the PCE paper; as described, the map buys "surjectivity" at the risk of bringing back the beaded bodies they already threw out, with no run showing otherwise. |
| The Retired Judge | GUILTY | The proposal is described as making all inheritance combinations possible, but the record admits it does not do that, and the defense itself asks for a narrower claim; a proposal that stands only after its own headline is cut back has failed as stated, whatever the off switch protects. |
| The Teenager | GUILTY | It's sold as "every combo can show up," but the weird ones people would actually screenshot, like a leg crossed with a jellyfish tentacle or anything on the round parts and main body, are left out or pushed to mutation, and the rest at a safe r are so rare that nobody will ever see them. |
| The Engineer | NOT GUILTY | This can be built and it fails safely: it sits behind a switch that is off by default, the first thing likely to break (beaded bodies when every r is above 0) can be measured with a test the project already has, and the overstated "all combinations" claim means the label should be narrowed to long parts, not that the build should stop. |
| The Small-Business Owner | GUILTY | The paper is the only thing that pays here, and this is spare-room work with nobody asking for it, no finish line ("rare" undecided, bead target unset) and a promise of "all combinations" it already admits it won't keep, so I wouldn't put Monday morning's hours into it as described. |
| The Statistician | NOT GUILTY | The only evidence against the map is 11 beaded bodies out of 45 children, a tiny sample from a variant that forced two switch points into every part, while a small r would only rarely give a part a second switch, so the expected bead rate sits close to the adopted 4/45 and nothing in the record shows the plan fails; behind an off switch, a test is the right next step. |
| The Parent | GUILTY | I would not let my own kid spend scarce time before a paper deadline on B-zone work that promises "all combinations" when its own defenders admit it only covers long parts, has never been tested, and has no finish line. |
| The Investor | GUILTY | I would not put my money into this as described, because the payoff is B-zone work the paper does not need, the headline promise of "all combinations" is already conceded to cover only long parts, and the only data on more switch points (11/45 beaded bodies against the adopted 4/45) points to losses, with no pass/fail bar to tell me when to stop paying. |
| The Designer | GUILTY | A stranger reading the headline would believe "every inheritance combination can appear," but the defense itself concedes the label must shrink to "surjective for long parts," with mutation covering the rest, so the plan as described promises something its own design does not deliver. |
| The Lawyer | GUILTY | I find no legal or regulatory trap in the record, and the off-by-default switch keeps the liability inside B-zone. But read as a promise, the proposal says "all inheritance combinations can appear" and its own known gaps say it does not, so it should not go ahead under that claim. |

### Charges that stuck

1. **It promises more than it does.** The headline says "every combination can appear," but round parts and the main body are left out and the below-0.25 pairs go to mutation (9 jurors).
2. **There is no finish line and no numbers.** No r values, no neighbour-pair counts and no chosen rarity line mean nobody can work out the cost or say when it has passed (4 jurors).
3. **It takes time from the paper.** This is B-zone work the IEEE CoG 2026 paper does not need, and its cost is unknown (4 jurors).

### What the defense got right

1. It sits behind a switch that is off by default, in the B-zone, so no current result or paper claim changes.
2. The bead risk has not been shown. The 11/45 figure came from parts that always had two switch points. A small r makes a second switch rare, and the existing 45-child linkage test can settle the question cheaply.

### Conditions for acquittal

1. Rename the claim "surjective for long-part gene combinations, off by default."
2. Write the pass bar before building anything: confirm a rarity line (5% or another number) and a maximum bead rate judged against the adopted 4/45, with every r above 0, count-placement included.
3. Write down the planned r values and pair counts, work out the rarest child's p and the matings that needs, and time-box the work into hours the paper does not need.

### The sentence

Do not build this under its current name. This week, narrow the claim to long parts, set the rarity line and the bead limit, and write down the r values. Then run the existing linkage test in spare hours only, and only after paper work is on schedule. If beads stay near 4/45, proceed. If not, stop.

_The full trial is in /home/claude/.court/20261115-180707: the opening statements, the rebuttals and every juror's vote._

_Made with [/court](https://github.com/alexyc9381/court-skill), a free Claude Code skill by Alex Chen ([@nocodealex](https://instagram.com/nocodealex))._
