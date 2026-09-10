# Asian Books Category

## Taxonomy

`CatalogCategory` uses the top-level `asian` category and five controlled subcategories:

- `chinese`
- `korean`
- `japanese`
- `south_asian`
- `southeast_asian`

Classification is deterministic and language-first. BCP-47-like language codes are normalized to lowercase hyphenated values (`zh-CN` becomes `zh-cn`); when no mapped language exists, title, author, and subject metadata are matched against regional terms. Every assignment stores `rule_version=asian-v1` for reproducibility. Scripts and transliteration belong in the explicit `CatalogBook.script` and `transliterated_title` fields; they should be populated by a later metadata connector rather than guessed from an English translation.

## Legal harvesting policy

Run:

```powershell
\.venv\Scripts\python.exe manage.py harvest_asian_catalog --limit 100
```

The command uses the existing Open Library, Internet Archive metadata, Standard Ebooks, and Project Gutenberg connectors. Project Gutenberg public-domain editions are available for in-platform reading. It persists only records marked `public_domain`, `open_license`, or `authorized` that also expose full text. `purchase_required`, `borrow`, `unknown`, and paywalled records are excluded. A provider's landing-page claim is not sufficient for a new connector: capture the license URL, verify the rights statement, record the verification timestamp, and retain the source URL and checksum before enabling in-app reading.

Recommended connectors and endpoints:

| Source | API / endpoint | Use |
| --- | --- | --- |
| Open Library | `https://openlibrary.org/search.json`, `https://openlibrary.org/works/{id}.json` | Discovery and identifiers |
| Project Gutenberg | Ebook pages and downloadable plain-text/EPUB resources | Public-domain editions |
| Internet Archive | `https://archive.org/advancedsearch.php` and item metadata API | Discovery; verify item rights before download |
| HathiTrust / national libraries | Institution-specific APIs or OAI-PMH | Metadata discovery only until rights are verified |

Respect `settings.BOOK_PROVIDER_USER_AGENT`, use a bounded timeout, cache metadata, rate-limit requests, retry only transient failures with backoff, and log provider, request URL, status, elapsed time, and error class. Do not scrape authenticated, robots-excluded, or paywalled pages.

## Metadata, files, and QA

The existing `CatalogBook` fields cover Dublin Core-style title, creator, language, date, identifier, source, and rights metadata. New fields capture `original_language`, `translated_language`, `license_url`, `license_verified_at`, `script`, and transliterated title. Use ISBN-13 as the primary edition key, then normalized title plus author; retain provider identifiers as provenance. SHA-256 checksums belong on imported file records and should be checked before replacing a file.

Before publishing an item, require a supported EPUB/PDF/TXT MIME type, a successful checksum, non-empty title and author, normalized language, a rights decision, and a source URL. Quarantine duplicate or conflicting-rights records for review. Monitor harvested count by provider/subcategory, license verification age, duplicate rate, failed downloads, checksum failures, and provider error rate. Back up the database and media together; test restore quarterly and retain immutable provenance records.

Useful checks:

```sql
SELECT subcategory, COUNT(*) FROM books_catalogcategory GROUP BY subcategory;
SELECT source, COUNT(*) FROM books_catalogbook
WHERE full_text_available = 1 AND copyright_status IN ('public_domain', 'open_license', 'authorized')
GROUP BY source;
```