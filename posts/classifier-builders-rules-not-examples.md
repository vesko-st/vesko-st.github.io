---
title: The Role of Jev-Style Classifiers in Modern Agentic Systems
subtitle: An agent can build and maintain the fast classifiers that do its repetitive work. Given labels, its natural-language classifiers rival fine-tuning; without them, it can interview the user instead.
byline: Veselin Stoyanov
og_desc: Agents can build natural-language classifiers that rival fine-tuned models, and build good ones from a small budget of the user's time when no labels exist.
twitter_desc: Agents can build their own fast classifiers, rivalling fine-tuning with labels and interviewing the user without them.
---

When [TypeSafe](https://typesafe.ai) released [Jev](https://docs.typesafe.ai/models) last month, it caught the imagination of those of us building with AI. Classifiers are not new, but in a world of highly capable language models we forgot that classifiers can be fast, cheap and useful. There is a good reason we were so quick to forget them: traditional classifiers are a pain to train, monitor, update and keep in sync with the rest of the system. But what if we could get the best of both worlds: an intelligent system that works in natural language, learns and adapts, and still performs its tasks quickly and cheaply? In other words, can an agent take over the painful part, and build and maintain the classifiers that do its high-volume, repetitive work?

TypeSafe calls Jev its [first System One model](https://docs.typesafe.ai/concepts/system-one), after the fast, intuitive mode of thinking in Daniel Kahneman's *[Thinking, Fast and Slow](https://en.wikipedia.org/wiki/Thinking,_Fast_and_Slow)*. In Kahneman's account, a task first takes the slow, deliberate effort of System 2; with practice, System 1 learns to do it quickly and automatically, while System 2 keeps watch and steps in when it errs. Most agentic systems today never make that hand-off: one frontier model plans, calls tools, and also makes every repetitive judgement, such as routing a message or deciding whether an email needs a reply, one item at a time. That is expensive, slow, and not always consistent. We would rather have the agent act as System 2: it works out how a task should be done, then builds, checks and updates a fast classifier that takes the task over as its System 1. A traditional classifier, trained by tuning its parameters, could play that role, but its decision rule lives in its weights, so changing it means relabelling and retraining. A *natural-language* (NL) classifier is a set of instructions and option descriptions that Jev answers, so the agent (and the user) can read and edit it like a document.

Can agents build and use NL classifiers effectively? We set out to answer this question empirically. We find that given the same labelled data, capable models build NL classifiers that rival and outperform strong fine-tuned baselines. And when no labelled data is available, agents can still build effective classifiers by spending a small budget of the user's time on labels and questions. We devise and test several active-learning strategies for spending that budget, deciding which records to label and what to ask the user, and the best of them produce classifiers close in accuracy to their supervised counterparts.

# The setup

The agent (Claude Opus) plays a classifier builder working for a user who needs a classifier. It gets a short task description, the list of classes, and about 1,000 unlabelled records. In the main setting it has a budget of 100 points of the user's time: a label costs 2 points, and a question about the definition costs 2, 5 or 10 points depending on how much it asks. A run that spends everything on labels gets about 50 of them. The user is simulated by another Claude Opus, which holds the gold labels and a private note, written beforehand from all of them, on how the labels apply the annotation policy. To establish a ceiling, we also give the builder every available training label and no budget. In both settings, we then use Jev to classify a hidden test set and measure the results.

We used six classical ML tasks, chosen so that what the builder has to learn sits in different places:

- **Banking77 intents**: 77 intents of customer messages to a bank. The definition is mostly in the text.
- **Banking77 routing**: the same messages, routed to 6 teams by a private mapping the builder has to discover.
- **Hate speech** ([HatEval](https://aclanthology.org/S19-2007/)): tweets labelled under an annotation policy nobody wrote down for the builder.
- **Persuasion strategy** ([Persuasion for Good](https://aclanthology.org/P19-1566/)): which of 18 strategies a persuader's message uses.
- **Donation outcome**: from the same dialogues, whether the persuadee ended up giving.
- **Deal reached** ([CraigslistBargain](https://aclanthology.org/D18-1256/)): whether a negotiation ended in a deal, with the closing offer removed.

The builder can shape the classifier however it wants. In practice it almost always ends up with a multiple-choice question whose options are finer than the classes and mapped back onto them, often three differently worded copies averaged together as an ensemble.

# With labels: as good as fine-tuning

First, the supervised case. We gave the Opus builder every training label and compared its NL classifier with RoBERTa fine-tuned on the same labels.


| Task                | Training labels | RoBERTa, fine-tuned | Opus NL classifier |
| ------------------- | --------------- | ------------------- | ------------------ |
| Banking77 intents   | 9,792           | 91.1                | **91.9**           |
| Banking77 routing   | 9,792           | 96.8                | **97.5**           |
| Hate speech         | 1,000           | 78.0                | **82.3**           |
| Persuasion strategy | 1,002           | 58.2                | **61.6**           |
| Donation outcome    | 500             | 67.5                | **68.0**           |
| Deal reached        | 4,947           | 88.9                | **89.6**           |


*Test scores: accuracy for the Banking77 tasks, macro-F1 for the rest, both on a 0–100 scale. One run per cell.*

The NL classifier matches or beats the fine-tuned encoder on all six tasks, by 3.4 to 4.3 points on hate speech and persuasion and by less than a point elsewhere, which we read as parity. It is not the state of the art: published full fine-tuning on Banking77 intents reaches 94.1. But it gets with specialized classifiers. Donation outcome is the odd one out: neither system beats a zero-shot classifier (73.3), because whether someone ends up donating is barely predictable from the conversation.

# Without labels: active learning with the user

The more common case for an agent is that no labelled data exists. Here the builder starts from the description and the unlabelled pool and spends its 100 points.


| Task                | Zero-shot | Opus, 100 points | Opus, all labels |
| ------------------- | --------- | ---------------- | ---------------- |
| Banking77 intents   | 80.2      | 86.8             | **91.9**         |
| Banking77 routing   | 73.7      | 91.3             | **97.5**         |
| Hate speech         | 74.1      | 78.9             | **82.3**         |
| Persuasion strategy | 45.5      | 60.3             | **61.6**         |
| Donation outcome    | **73.3**  | 71.7             | 68.0             |
| Deal reached        | 88.9      | 88.0             | **89.6**         |


*Zero-shot is a Jev classifier built from the class names and description alone. The 100-point column averages 3 to 15 runs per task, across strategies.*

Wherever the user has something to teach, about 50 labels' worth of their time beats zero-shot by a wide margin: 6.6 points on intents, 17.6 on routing, 4.8 on hate speech and 14.8 on persuasion. On hate speech and persuasion, the budgeted classifiers even beat RoBERTa fine-tuned on twenty times as many labels (78.9 against 78.0, and 60.3 against 58.2). On donation and deal, zero-shot is already at the ceiling and there is nothing to learn.

## Active-learning strategies

How the agent spends the budget matters, so we devised a set of strategies, each a one-page instruction that tells the builder which records to label, when to ask the user, and when to keep a revision:

- **Free**: the builder decides for itself.
- **Uncertainty**: label the records the classifier is least sure about, in small batches, revising after each.
- **Uncertainty + rules**: the same, but turn errors into general rules, and check any rule that moves many records with a label on one of them before trusting it.
- **Policy first**: ask the user about the main policy decisions, build a classifier that mirrors the answers, then calibrate it with labels.
- **Policy, labels first**: check the draft against random labels before asking about edge cases, so that labels can overrule the user's answers.
- **Interview, lean**: read the pool, which is free, ask only about what the text cannot settle, and spend the rest on whatever labels the builder needs.

| Strategy             | Intents  | Routing  | Hate speech | Persuasion | Donation | Deal     | Gap closed |
| -------------------- | -------- | -------- | ----------- | ---------- | -------- | -------- | ---------- |
| Free                 | 86.3     | 92.8     | 79.9        | **60.6**   | 70.6     | 87.3     | 74%        |
| Uncertainty          | **87.9** | 87.4     | 75.1        | 58.5       | **73.4** | 89.0     | 54%        |
| Uncertainty + rules  | 87.4     | 88.9     | **80.7**    | **60.6**   | 73.3     | **90.8** | 75%        |
| Policy first         | 86.2     | 93.4     | 78.9        | 60.3       | 69.3     | 88.5     | 71%        |
| Policy, labels first | 86.6     | **94.0** | 80.1        | 60.0       | 71.9     | 84.2     | **76%**    |
| Interview, lean      | 86.3     | 93.2     | 79.9        | 60.0       | 72.0     | 85.3     | 74%        |

*Opus builders, 100 points, test set. All routing cells, the lean interview row, and most intents and hate speech cells average three runs; the rest are single runs. Gap closed is the share of the distance from zero-shot to the all-labels classifier that a strategy covers, averaged over intents, routing, hate speech and persuasion; on donation and deal, zero-shot is already at or above all labels, so there is no gap to close.*

The best strategy depends on where the missing knowledge lives. On Banking77 intents, whose meaning is in the text, uncertainty sampling works best, and spending a third of the budget on questions costs 1.7 points. On routing, where the mapping of intents to teams is private, uncertainty sampling is the worst choice: a counter-intuitive assignment sends a whole intent to the wrong team with confidence, so its records never look uncertain. Every run that asked about the routing rules, or bought a label for each intent it could not place, scored 92–95, against 85–90 for every uncertainty run; one round of questions about the routing rules took a first draft from about 80 to 92–94. On hate speech, where the labels follow a policy the builder cannot infer (hate against women and immigrants only), the builder can learn the policy either by asking about it or by turning labelled errors into rules: uncertainty + rules reached 80.7 without asking a single question. Only pure uncertainty sampling, which swings the decision boundary with each noisy batch of labels, falls behind. Where nothing much is left to learn, questions can hurt: on deal reached, every classifier saved right after the user's answers about borderline negotiations scored lower than the draft before it. Averaged over the tasks with something to learn, policy with labels first, uncertainty + rules, free and the lean interview all close about three quarters of the gap to all labels, but no strategy is best everywhere.

The simulated user turned out to matter as much as the strategies. Our first version answered from the written policy and a small labelled sample, and its answers about edge cases were stricter than its own labels, as annotation guidelines often are stricter than annotators. Builders that took its answers at face value lost accuracy, and asking about the policy first looked like the clear winner on hate speech. Once the simulated user knew how its labels actually apply the policy, that lead disappeared.

# What the classifiers learn

The finished classifiers are compact, readable definitions. Counting the rules in each (the sentences and list items of its instructions and option descriptions) gives a picture of what the builder wrote:

| Task                | Classes | Options | Rules     | Exclusion rules | Words         |
| ------------------- | ------- | ------- | --------- | --------------- | ------------- |
| Banking77 intents   | 77      | 77 (77) | 117 (181) | 38 (51)         | 1,892 (2,413) |
| Banking77 routing   | 6       | 77 (93) | 87 (117)  | 22 (15)         | 896 (969)     |
| Hate speech         | 2       | 12 (13) | 22 (26)   | 4 (8)           | 500 (505)     |
| Persuasion strategy | 18      | 23 (18) | 36 (24)   | 8 (1)           | 896 (553)     |
| Donation outcome    | 2       | 8 (10)  | 16 (18)   | 6 (6)           | 317 (293)     |
| Deal reached        | 2       | 8 (5)   | 16 (9)    | 6 (4)           | 402 (161)     |

*Medians over the final classifiers of all budgeted Opus runs (every strategy, 10 to 23 runs per task); in brackets, the single classifier Opus built from all labels. Counts are for one member of the ensemble, as members are rewordings of each other. Exclusion rules are those that say what does not belong ("not", "rather than", "unless", "except").*

Three things stand out. The builders almost always ask for finer distinctions than the task does: binary tasks get 8 to 12 options, and routing's 6 teams are reached through the 77 intents, each mapped to its team. A good share of the rules, a fifth to a third, are exclusions that mark a boundary with a neighbouring option, which is where the classifier's errors are. And the definitions stay short: a few hundred words for a binary task, under 2,000 for 77 intents, so that a person can read the whole classifier in a few minutes. Ten to two hundred times as many labels do not make a classifier much bigger: from all labels, Opus wrote more rules on the Banking77 tasks and fewer on the conversation tasks, where budgeted builders padded their definitions with the records they had bought (more on that below). Building them is visible too: the builders that logged their reasoning wrote 580 hypotheses across 46 runs (a median of 10 per run), and dropped roughly one in six of them after testing them on the pool.

# A smaller finding: rules, not examples

Comparing the budgeted classifiers with the ones built from every label, we expected the extra labels to buy a different kind of classifier. They did not: the shapes are the same. What differs is what the definitions contain. With a budget, builders paste the labels they bought into the definition: one persuasion classifier has a field on every option called "labelled examples of messages tagged this way", filled with real lines from the data, typos included ("So would you like to throw these wonderful kills a buck ?"). With every label, builders copy almost nothing and describe patterns instead, because no handful of examples is representative of a thousand records. An example only describes itself, and the classifier will never see that record again at test time.

So we told budgeted builders that labels are evidence for rules and never part of the classifier: state what a mislabelled record shares with its class as a rule about meaning, test the rule on other records, and keep it only if it holds beyond the record that prompted it. Across five runs matched to earlier uncertainty-sampling runs, the rules-only classifiers contained no pool text, against up to 56 pasted records in the baselines, and scored level or slightly higher. The gains were where the baseline had pasted most: persuasion strategy rose from 58.5 to 61.5, and deal reached from 89.0 to 90.4. These are single runs, so we read them as "examples are not needed" rather than "rules are reliably better".

The resulting definitions read like an annotation guide. The persuasion builder, for instance, found that questions about the partner's own giving count as personal inquiries, the opposite of what its baseline had decided, and it dropped a hypothesis that moved 13 records on the strength of a single label.

# What we take away

The main answer to the question we started with is yes: an agent can build accurate classifiers on its own. Given the same labels, an Opus builder matches or beats RoBERTa fine-tuned on them on all six tasks. With no labelled data and a budget of about 50 labels' worth of the user's time, it beats zero-shot wherever the user has something to teach, and on two tasks it beats an encoder fine-tuned on twenty times as many labels. And because the classifier is written in plain language, it can be read, audited and changed in one place when the policy changes.

We are releasing the recipes we use: the builder skill, the labelling and questioning strategies, and the tools that go with them, at [LINK]. This is also how we are bringing Jev into [Lightfield](https://lightfield.app): rather than hand-building classifiers, our agent builds and maintains them from a description and a few answers from the user, and Jev runs them over many items quickly and cheaply.