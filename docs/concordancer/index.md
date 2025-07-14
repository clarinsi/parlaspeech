---
layout: default
title: How to Use the Concordancer
---

# Using the ParlaSpeech Concordancer

The **ParlaSpeech Concordancer** enables detailed linguistic and prosodic searches in the **ParlaSpeech v3 corpus**.  
This guide provides a walkthrough of its basic and advanced functionalities, designed for both linguists and interested non-specialists.

---

## 1. Simple Search (Lemma)

Suppose you are interested in the verb **"uspostaviti"** ("to establish").  
You can begin with a **lemma search**, which retrieves **all inflectional forms** of that lemma.

### Query: uspostaviti


This will return occurrences of various forms, such as:

- **uspostavi**  
- **uspostavljamo**  
- **uspostavljena**, etc.

---

![Screenshot: Simple lemma search](../img/1_uspostaviti.png)

---

## 2. Simple Search (Word Form)

To search for a **specific word form**, you can input the word directly. For example:

### Query: uspostavi


**Why refine the search?**

The form **uspostavi** is **ambiguous**. It may function as:

- **Verb** (e.g., _"He/She establishes"_)  
- **Noun** (in some specialized or archaic contexts)

To avoid retrieving unrelated occurrences, further filtering is needed.


## 3. Advanced Search: CQL with Part of Speech (POS)

To disambiguate between different **parts of speech**, use **Corpus Query Language (CQL)**.  
In this case, to extract only the **verb** usages of *uspostavi*, the query is:

### Query: [word="uspostavi" & pos="VERB"]


#### Annotation Standards:

- **word** – surface form  
- **pos** – **Universal Dependencies (UD)** part-of-speech tag

This ensures your search is **morphosyntactically precise**.

---

![Screenshot: CQL with POS](../img/2_uspostavi_verb.png)

---

## 4. Advanced Search: Prosodic Features (Primary Stress)

The ParlaSpeech corpus includes **prosodic annotations**, such as **primary stress placement**.

For example, the **verb** *uspostavi* is typically pronounced with **stress on the 2nd syllable**.

### Query: [word="uspostavi" & pos="VERB" & primary_stress="2"]

To explore variation or errors, you might query for **stress on the 3rd syllable**:

### Query: [word="uspostavi" & pos="VERB" & primary_stress="3"]

#### About `primary_stress`:

- Indicates the **syllable index** where stress is realized (1-based).  
- Acceptable values: `1` to *N* (number of syllables in the word).

---

![Screenshot: CQL with primary stress](../img/3_uspostavi_verb_prim_stress2.png)

---

## 5. Filled Pause Contexts

The concordancer also encodes **disfluency markers**, including **filled pauses (FP)** such as _"eee"_ or _"umm"_.

To find occurrences where *račun* is followed by a filled pause:
### Query: [word="račun" & fp_after="1"]


To find occurrences where a filled pause precedes the word:
### Query: [word="račun" & fp_before="1"]


#### Interpretation:

- `fp_after` and `fp_before` can take values:
    - `1` – Filled pause is present  
    - `0` – No filled pause

This feature is valuable for research on **speech disfluencies**, **planning phenomena**, and **prosody-syntax interfaces**.

---

![Screenshot: CQL with filled pause](../img/4_racun_fp_after.png)

---

## Summary of Query Types

| Search Type                     | Example |
|---------------------------------|---------|
| Simple lemma search             | `uspostaviti` |
| Simple word form search         | `uspostavi` |
| CQL: POS disambiguation         | `[word="uspostavi" & pos="VERB"]` |
| CQL: Stress on 2nd syllable     | `[word="uspostavi" & pos="VERB" & primary_stress="2"]` |
| CQL: Stress on 3rd syllable     | `[word="uspostavi" & pos="VERB" & primary_stress="3"]` |
| CQL: Filled pause after "račun" | `[word="račun" & fp_after="1"]` |

---

## Available Attributes

| Attribute         | Description |
|------------------|-------------|
| **word**          | Surface form (orthographic) |
| **lemma**         | Lemma (canonical form) |
| **pos**           | Part of speech (UD standard) |
| **primary_stress**| Primary stress position (syllable index) |
| **fp_before**     | Filled pause before word (0 = no, 1 = yes) |
| **fp_after**      | Filled pause after word (0 = no, 1 = yes) |

---

## Additional Notes

- All searches are **case-insensitive(?)** by default.
- It is suggested to **play each audio segment** (red play button on the right side) to verify it is correctly annotated.
- On the top right-side, the **eye icon** can be used to display information for each individual token for easier searching.
- The system uses **Universal Dependencies (UD)** annotation conventions for morphology and syntax.
- Prosodic and disfluency annotations extend standard corpus search functionality into **speech-oriented analysis**.

---

For more information, visit the [ParlaSpeech main page](../index.html).

