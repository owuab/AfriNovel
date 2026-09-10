# Upload Book Handoff

## Current implementation

The Publish page accepts one required manuscript, one optional cover, and multiple optional supporting assets in a single multipart submission. Uploads are stored as `BookUpload` records linked to the new draft `Book` and authenticated uploader.

Supported formats:

- Primary manuscript: EPUB for reflowable reading, PDF for fixed-layout books, DOCX for author compatibility, and MOBI for legacy Kindle files.
- Cover: JPG, PNG, or WEBP for browser previews and broad image support.
- Supporting assets: ZIP for bundled material, plus images and PDF.

The current server limit is 50 MB per file. Filenames are reduced to a safe basename for metadata and a UUID-based storage path prevents collisions and path traversal. Content type is retained for later processing.

## UX behavior

The upload area supports keyboard file picking, drag-and-drop, multiple assets, file name/size summaries, client-side extension and size validation, cover preview, live status announcements, and a visible upload state on submit. Existing metadata and draft moderation behavior are unchanged.

## Security and processing plan

The server must remain authoritative. Before marking an upload ready in production, run MIME/signature validation, antivirus scanning, archive bomb checks, decompression limits, and PII/content policy checks in an asynchronous worker. Store uploads in private S3-compatible object storage with server-side encryption, short-lived signed URLs, lifecycle retention rules, and per-user rate limits. Do not serve original uploads directly from a public media path in production.

Recommended states are `pending`, `processing`, `ready`, and `failed`; the model already includes these states for a worker integration. Persist error codes separately from user-facing localized messages when the processing worker is introduced.

## API evolution

The current form is a same-origin multipart POST to `/publish/`. For large files, add:

- `POST /api/uploads/initiate/`: authenticate, authorize, return upload ID and chunk size.
- `PUT /api/uploads/{id}/parts/{number}/`: upload a chunk with checksum.
- `POST /api/uploads/{id}/complete/`: verify all parts and enqueue scanning.
- `GET /api/uploads/{id}/status/`: return status, progress, error code, and preview URL.
- `POST /api/books/{id}/submit/`: link ready files to metadata and submit for moderation.

Use S3 multipart upload or tus rather than holding large files in Django memory. Preserve `title`, `author`, `ISBN`, and version in a future `BookEdition` metadata object if editions are required.

## Acceptance tests

- Authenticated authors can submit an EPUB and the book remains `draft`.
- Missing manuscript, unsupported extension, and files over 50 MB are rejected without creating a book.
- Cover preview works without uploading the file to the server first.
- Multiple assets are stored independently and linked to the same book.
- Anonymous users are redirected to login; users cannot attach files to another author's book.
- Malware, invalid signatures, oversized archives, and failed processing produce retryable errors.
- Keyboard-only operation, screen-reader announcements, focus visibility, RTL layout, reduced motion, and WCAG AA contrast pass.
- Load target: initial upload UI adds no third-party runtime dependency; async processing keeps request latency independent of file conversion.

## Rollout

1. Deploy migration `0015_bookupload` and private storage configuration to staging.
2. Run the publish/upload, security, accessibility, and cross-browser test checklist.
3. Enable asynchronous scanning and preview generation before production uploads are considered ready.
4. Monitor upload failures, file sizes, processing duration, storage growth, and retry rates.

Rollback is application-only: disable the upload controls and route while retaining the additive `BookUpload` table, or restore the previous template/view. No existing book metadata is changed by this feature.
