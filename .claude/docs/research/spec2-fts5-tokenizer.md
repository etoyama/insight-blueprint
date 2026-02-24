# SQLite FTS5 Tokenizer Options for Japanese+English Mixed Content

Research Date: 2026-02-24

## Overview

This document evaluates SQLite FTS5 tokenizer options for full-text search on content
that mixes Japanese (kanji, hiragana, katakana) with English text. Three main approaches
are compared: the built-in unicode61/trigram tokenizers, the ICU tokenizer extension, and
the better-trigram extension.

---

## 1. Built-in Tokenizers

### 1.1 unicode61 (Default)

The unicode61 tokenizer classifies characters as "separator" or "token" based on Unicode 6.1
standards. All space and punctuation characters are separators; everything else is a token
character.

**Configuration Options:**
- `remove_diacritics` - 0, 1 (default), or 2
- `tokenchars` - Additional characters to treat as tokens (e.g., hyphens)
- `separators` - Force characters to be separators
- `categories` - Unicode general categories treated as tokens (default: `L* N* Co`)

**CJK Limitation:**
unicode61 relies on whitespace/punctuation to detect word boundaries. CJK languages lack
explicit word boundaries between characters, so the entire run of CJK characters becomes a
single token. This makes it impossible to search for individual words within a Japanese sentence.

```sql
-- unicode61: Japanese text becomes ONE big token
CREATE VIRTUAL TABLE ft USING fts5(content, tokenize='unicode61');
INSERT INTO ft(content) VALUES ('日本語のテキスト検索');
-- MATCH 'テキスト' will NOT find the row (substring not a separate token)
```

**Verdict: NOT suitable for Japanese text.**

### 1.2 trigram (Built-in)

The trigram tokenizer treats each contiguous sequence of 3 characters as a token, enabling
substring matching.

**Configuration Options:**
- `case_sensitive` - 0 (default) or 1
- `remove_diacritics` - 0 (default) or 1

```sql
CREATE VIRTUAL TABLE ft USING fts5(content, tokenize='trigram');
INSERT INTO ft(content) VALUES ('日本語のテキスト検索');
-- MATCH 'テキスト' WILL find the row (substring match via trigrams)
SELECT * FROM ft WHERE ft MATCH 'テキスト';
```

**Pros:**
- Built-in, no extensions needed
- Substring matching works for Japanese
- Supports LIKE and GLOB patterns with indexing

**Cons:**
- Minimum 3-character query required (single kanji or 2-char words won't match)
- Larger index size (every 3-char sequence is indexed)
- No linguistic awareness (no stemming, no word boundaries)
- Single kanji characters (which ARE valid Japanese words) cannot be searched

**Verdict: Workable for Japanese if queries are 3+ characters. Has a critical gap for
1-2 character searches.**

### 1.3 porter (Wrapper)

Applies Porter stemming to an underlying tokenizer. Only useful for English morphological
matching (e.g., "running" matches "run"). No benefit for Japanese.

### 1.4 ascii

Treats all non-ASCII characters as token characters. Same fundamental limitation as
unicode61 for CJK -- no word boundary detection.

---

## 2. Extension Tokenizers

### 2.1 ICU Tokenizer (fts5-icu-tokenizer)

Uses the International Components for Unicode (ICU) library for language-aware word
segmentation.

**Source:** https://github.com/cwt/fts5-icu-tokenizer

**Japanese-specific features:**
- Transformation rule: `NFKD; Katakana-Hiragana; Lower; NFKC`
- Proper word boundary detection for kanji, hiragana, katakana
- Locale-aware segmentation (locale code: `ja`)

**Installation:**
```bash
# Prerequisites: cmake, C compiler, libsqlite3-dev, libicu-dev
mkdir build && cd build
cmake .. -DLOCALE=ja
make
```

**Usage:**
```sql
.load ./build/libfts5_icu_ja.so

CREATE VIRTUAL TABLE documents_ja USING fts5(
    content,
    tokenize = 'icu_ja'
);

INSERT INTO documents_ja(content) VALUES ('日本語テキスト');
SELECT * FROM documents_ja WHERE documents_ja MATCH 'テキスト';
```

**Pros:**
- Linguistically accurate word segmentation for Japanese
- Handles kanji, hiragana, katakana correctly
- Supports normalization (Katakana-Hiragana conversion, case folding)
- Proper handling of mixed Japanese+English content

**Cons:**
- Requires external C extension (compilation step)
- Depends on ICU library (large dependency)
- Word segmentation can be ambiguous (same phrase can tokenize multiple ways)
- Not available in standard SQLite distributions or Python's sqlite3 module
- Deployment complexity (need to ship .so/.dylib)

**Verdict: Best linguistic quality, but heavy deployment requirements.**

### 2.2 better-trigram

An improved trigram tokenizer that treats CJK characters individually instead of as
trigram sequences.

**Source:** https://github.com/streetwriters/sqlite-better-trigram

**Key difference from built-in trigram:**
- CJK characters are tokenized individually (each character = 1 token)
- Non-CJK text uses standard trigram tokenization
- Mixed content handled automatically

**Example tokenization:**
```
Input: "李红：那是钢笔 hello world"
Tokens: ['李','红','：','那','是','钢','笔','hel','ell','llo',' ll','llo','lo ','o w',' wo','wor','orl','rld']
```

**Installation:**
```bash
# Prerequisites: lemon, tcl
# macOS
brew install lemon tcl-tk
# Linux
sudo apt install lemon tcl

make loadable
```

**Usage:**
```sql
.load ./better_trigram

CREATE VIRTUAL TABLE ft USING fts5(content, tokenize='better_trigram');
```

**Pros:**
- Single CJK character search works (solves trigram's 3-char minimum)
- 1.6x faster than standard trigram
- Mixed CJK + English handled automatically
- No large external dependencies (unlike ICU)

**Cons:**
- Still requires external C extension
- No linguistic word segmentation (character-level, not word-level)
- Still no stemming or morphological analysis

**Verdict: Good balance between capability and complexity for mixed content.**

---

## 3. Comparison Matrix

| Feature | unicode61 | trigram | ICU (ja) | better-trigram |
|---|---|---|---|---|
| Built-in | Yes | Yes | No (ext) | No (ext) |
| Japanese word search | No | Partial (3+ chars) | Yes | Yes (char-level) |
| Single kanji search | No | No | Yes | Yes |
| English word search | Yes | Yes (3+ chars) | Yes | Yes (3+ chars) |
| Mixed JP+EN | No | Partial | Yes | Yes |
| Linguistic accuracy | N/A | None | High | None |
| Index size | Small | Large | Medium | Medium-Large |
| Deployment complexity | None | None | High (ICU dep) | Medium (C ext) |
| Min query length | 1 token | 3 chars | 1 word | 1 char (CJK) / 3 chars (Latin) |
| Python sqlite3 compatible | Yes | Yes | No | No |

---

## 4. Recommendations for insight-blueprint

### Option A: Built-in trigram (Recommended for MVP)

Use the built-in trigram tokenizer for zero-dependency deployment. Accept the 3-character
minimum query limitation for Japanese text.

```sql
CREATE VIRTUAL TABLE analysis_fts USING fts5(
    title,
    body,
    tags,
    tokenize='trigram',
    content='analysis',
    content_rowid='id'
);

-- Search works for 3+ character Japanese queries
SELECT a.* FROM analysis a
JOIN analysis_fts f ON a.id = f.rowid
WHERE analysis_fts MATCH 'テキスト'
ORDER BY rank;

-- Also works for English
SELECT a.* FROM analysis a
JOIN analysis_fts f ON a.id = f.rowid
WHERE analysis_fts MATCH 'hypothesis'
ORDER BY rank;

-- For short queries (1-2 chars), fall back to LIKE
SELECT * FROM analysis WHERE title LIKE '%仮%' OR body LIKE '%仮%';
```

**Mitigation for short queries:**
- Use LIKE fallback for queries < 3 characters
- Document this limitation in the API

### Option B: ICU tokenizer (Best quality, complex deployment)

If high-quality Japanese search is critical, use the ICU tokenizer. Requires bundling
the compiled extension.

```sql
.load ./libfts5_icu_ja

CREATE VIRTUAL TABLE analysis_fts USING fts5(
    title,
    body,
    tags,
    tokenize='icu_ja',
    content='analysis',
    content_rowid='id'
);

-- Word-level search works perfectly
SELECT * FROM analysis_fts WHERE analysis_fts MATCH 'テキスト';
```

### Option C: Dual-index approach (Advanced)

Maintain two FTS indexes: trigram for substring matching and unicode61 for English
word matching. Query both and merge results.

```sql
-- English-optimized index
CREATE VIRTUAL TABLE analysis_fts_en USING fts5(
    title, body,
    tokenize='porter unicode61',
    content='analysis',
    content_rowid='id'
);

-- Japanese-optimized index (trigram for substring match)
CREATE VIRTUAL TABLE analysis_fts_jp USING fts5(
    title, body,
    tokenize='trigram',
    content='analysis',
    content_rowid='id'
);
```

This doubles storage but provides English stemming + Japanese substring matching.

---

## 5. Practical SQL Examples

### Content-Sync (External Content Tables)

```sql
-- Main table
CREATE TABLE analysis (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    body TEXT,
    tags TEXT
);

-- FTS index (external content)
CREATE VIRTUAL TABLE analysis_fts USING fts5(
    title,
    body,
    tags,
    content='analysis',
    content_rowid='id',
    tokenize='trigram'
);

-- Triggers to keep FTS in sync
CREATE TRIGGER analysis_ai AFTER INSERT ON analysis BEGIN
    INSERT INTO analysis_fts(rowid, title, body, tags)
    VALUES (new.id, new.title, new.body, new.tags);
END;

CREATE TRIGGER analysis_ad AFTER DELETE ON analysis BEGIN
    INSERT INTO analysis_fts(analysis_fts, rowid, title, body, tags)
    VALUES ('delete', old.id, old.title, old.body, old.tags);
END;

CREATE TRIGGER analysis_au AFTER UPDATE ON analysis BEGIN
    INSERT INTO analysis_fts(analysis_fts, rowid, title, body, tags)
    VALUES ('delete', old.id, old.title, old.body, old.tags);
    INSERT INTO analysis_fts(rowid, title, body, tags)
    VALUES (new.id, new.title, new.body, new.tags);
END;
```

### MATCH Query Patterns

```sql
-- Basic search
SELECT * FROM analysis_fts WHERE analysis_fts MATCH 'keyword';

-- Column-specific search
SELECT * FROM analysis_fts WHERE analysis_fts MATCH 'title:keyword';

-- Boolean operators
SELECT * FROM analysis_fts WHERE analysis_fts MATCH 'keyword1 AND keyword2';
SELECT * FROM analysis_fts WHERE analysis_fts MATCH 'keyword1 OR keyword2';
SELECT * FROM analysis_fts WHERE analysis_fts MATCH 'keyword1 NOT keyword2';

-- Phrase search (trigram)
SELECT * FROM analysis_fts WHERE analysis_fts MATCH '"exact phrase"';

-- Ranked results
SELECT *, rank FROM analysis_fts WHERE analysis_fts MATCH 'query' ORDER BY rank;

-- With highlight snippets
SELECT highlight(analysis_fts, 0, '<b>', '</b>') as title,
       snippet(analysis_fts, 1, '<b>', '</b>', '...', 64) as body_snippet
FROM analysis_fts
WHERE analysis_fts MATCH 'query';
```

---

## Sources

- [SQLite FTS5 Official Documentation](https://sqlite.org/fts5.html)
- [FTS5 ICU Tokenizer (GitHub)](https://github.com/cwt/fts5-icu-tokenizer)
- [better-trigram Tokenizer (GitHub)](https://github.com/streetwriters/sqlite-better-trigram)
- [SQLite Users Mailing List: unicode61 and CJK](https://sqlite-users.sqlite.narkive.com/N5MOmskp/sqlite-why-sqlite-fts5-unicode61-tokenizer-does-not-support-cjk-chinese-japanese-krean)
- [Chroma FTS5 trigram CJK issue](https://github.com/chroma-core/chroma/issues/1073)
