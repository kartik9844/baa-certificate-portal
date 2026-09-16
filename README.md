# BAA Certificate Portal

A fully static certificate-verification website for Basava Acu Academy (BAA).
No backend, no database — a public-read Google Cloud Storage bucket holds
certificate files and small "index" JSON files, and the static site (hosted on
GitHub Pages) does client-side lookups by fetching only the one index file
that matches what a person typed. It never downloads a full list of students.

## 1. Bucket layout & hash scheme

```
gs://certificate_baa/
  certs/<random-id>-<certno-lowercase>.jpg
  index/by-name/<hash>.json
  index/by-phone/<hash>.json
  index/by-email/<hash>.json
  index/by-certno/<hash>.json
```

Each index JSON file is an array of records that share the same hash:
```json
[{ "name": "A Raghavendra", "cert_no": "BAATEM25-26083", "file": "certs/xxxx-baatem25-26083.jpg" }]
```

`hash = SHA256(SALT + normalized_value)`, where:
- **name**: trim, lowercase, collapse internal whitespace to a single space
- **phone**: digits only; if more than 10 digits, keep the last 10 (tolerates a
  leading country code like `+91`)
- **email**: trim, lowercase
- **cert_no**: trim, uppercase

The SALT is a fixed, non-secret string. It must be **identical** in both
places that compute hashes:
- `public/assets/config.js` (used by `index.html`)
- `tools/bootstrap_bucket.py` (Python can't import the `.js` file, so it has
  its own literal copy — a comment there says "MUST match config.js exactly")

(`public/gen/index.html` doesn't hash or index anything — see §5.)

Certificate filenames include a random component so they can't be enumerated
by guessing adjacent numbers, even though the underlying certificate numbers
(`BAATEM25-XXXXX`) are sequential.

## 2. How the original 2,203 certificates were generated

This already existed before the website work:
- `sort_assign_certificates.ps1` sorts the master list by name and assigns
  sequential `CERTIFICATE NO` values (`BAATEM25-26083`, `BAATEM25-26084`, …).
- `generate_certificates.ps1` renders each student's Name and Certificate No.
  onto the template image (`Add a subheading (1).png`) using GDI+
  (`System.Drawing`), producing `sorted_certificates/<CertNo>.jpg`.

These scripts are unchanged by this project — they're the source of the 2,203
JPGs and of the exact text placement/font rules that `public/gen/index.html`
re-implements in the browser (see §4).

## 3. Bootstrap tool — one-time migration of the existing 2,203 certs

`tools/bootstrap_bucket.py` converts the already-rendered certificates into
the bucket-ready structure above: it renames (copies, never mutates the
originals) each `sorted_certificates/<CertNo>.jpg` to
`gcs_upload/certs/<random-id>-<certno-lower>.jpg`, and builds the merged
`gcs_upload/index/by-{name,phone,certno}/<hash>.json` files from
`2025 TEM - CERTIFICATE ISSUE_SORTED_WITH_BATCH_CODES.xlsx` (columns
Name/Phone×2/Certificate No). There's no email column in the current data, so
no `by-email` files are produced by this script — but the site's email search
path still works for any record added later via `/gen` with an email filled in.

```
pip install openpyxl
python tools/bootstrap_bucket.py --dry-run --limit 5   # sanity check first
python tools/bootstrap_bucket.py                       # full run -> gcs_upload/
```

This script only reads local files. It never uploads anything and never
touches `credentials/gcs_key.json` — upload `gcs_upload/` to the bucket
yourself (Console or `gsutil -m cp -r gcs_upload/* gs://certificate_baa/`).

**Known data issue found on the last run:** row SL NO 2203
(`BAATEM25-28285`) has a blank Name cell in the spreadsheet, so it was
correctly skipped — that certificate has no student name to index against.
Fix the spreadsheet and re-run the script if this student should be
searchable.

**Critical correctness check before uploading:** the Python hashing must
produce byte-for-byte identical output to the JS hashing for the same input.
Verify with e.g.:
```
python -c "import hashlib; print(hashlib.sha256(('s5nF3nbmO9rbo6azJFqnmXPBhuVaDVop'+'BAATEM25-26083').encode('utf-8')).hexdigest())"
```
...and comparing against the browser console's `hashFor('cert_no', 'BAATEM25-26083')`
on the live search page. If SALT/normalization/encoding ever drift between
`config.js` and `bootstrap_bucket.py`, lookups will silently 404 forever with
no visible error.

## 4. Public search site (`public/index.html`)

One input + button (+ Enter key). Auto-detects what was typed: 10–12 digits
after stripping non-digits → phone; contains `@` → email; otherwise tries both
name and certificate number in parallel. It computes the relevant SHA-256
hash(es) client-side and fetches only `index/<field>/<hash>.json` — never a
full list. Results are merged/de-duplicated by `cert_no`, shown as a clickable
list, and clicking shows the certificate inline (`<img>` for JPG/PNG, `<embed>`
for PDF) plus a direct "Download Certificate" link to the GCS file.

**Going live checklist:**
- [ ] Replace the placeholder `SALT` in `public/assets/config.js` **and**
      `tools/bootstrap_bucket.py` with your own value, then re-run the
      bootstrap script and re-upload `gcs_upload/`.
- [ ] Confirm `BUCKET_BASE_URL` in `config.js` is correct.
- [ ] Replace the placeholder `ADMIN_PASSPHRASE` in `public/gen/index.html`.

## 5. Admin page (`public/gen/index.html`) — hidden, unlinked

For quickly generating a certificate image for someone who was missed during
the original bulk run — e.g. to send directly to the student. Not linked from
anywhere; disallowed in `robots.txt`; has a `noindex,nofollow` meta tag.

- **Passphrase gate is not real security.** It's plain client-side JS, fully
  visible via "View Source" — its only purpose is to stop an accidental
  stumble onto the URL.
- Fields: Name, Certificate Number. On submit, it draws them onto the
  template (same rect/coordinates/font-shrink rule as
  `generate_certificates.ps1` — see below) and offers a "Download
  Certificate" button that saves the plain JPG.
  Caveat: browser Canvas 2D and the original GDI+ renderer use different font
  metrics, so this is a close visual match, not pixel-identical.
- **This does not touch the bucket or the search index.** A certificate
  generated here is *not* searchable on the public site — it's only for
  handing/sending directly to that one person. If it should also be
  searchable, add it to the bucket separately (see `tools/bootstrap_bucket.py`
  for the batch pattern, or upload it and its index files by hand following
  the bucket layout in §1).

## 6. GCS bucket setup (done for `certificate_baa` — kept here for reference / for setting up a new bucket)

**Status: done and verified live.** `allUsers` is granted
`roles/storage.legacyObjectReader` (get-only, no list) and CORS allows GET
from `https://kartik9844.github.io`. Confirmed: object fetches return 404 for
missing files (not 403), and anonymous bucket listing returns 401.

1. **Public read, object-level only — do not grant `Storage Object Viewer`.**
   It looks like the obvious "public read" role, but it also grants
   `storage.objects.list`, which lets anyone enumerate every object in the
   bucket — defeating the whole point of random filenames. Use
   **`roles/storage.legacyObjectReader`** instead: it grants only
   `storage.objects.get`, and (unlike a custom role) doesn't require
   `iam.roles.create` permission — just bind it to `allUsers` on the bucket.
2. **CORS**, required because the search page's `fetch()` calls to
   `index/**/*.json` are cross-origin (GitHub Pages → storage.googleapis.com).
   `<img>`/`<embed>`/direct download links do *not* need this.
   ```
   gsutil cors set cors.json gs://certificate_baa
   ```
   (`cors.json` in this repo already has the real Pages origin filled in.)
3. **Write access**: `/gen` doesn't upload anything, so no team member needs
   bucket IAM just to use it. If you separately want people able to upload
   new batches themselves (rather than asking for that to be done for them),
   grant `Storage Object Creator`, scoped to just this bucket, to those
   people. No write credentials of any kind exist in this codebase.

## 7. Deployment

GitHub Actions (`.github/workflows/deploy.yml`) deploys `public/` to GitHub
Pages on every push to `main`. Zero repository secrets are needed — the
bucket is public-read for GET only, and there is no write step in CI.

One-time manual step: in the repo's **Settings → Pages → Source**, choose
**"GitHub Actions"**.

## 8. Local testing (before uploading anything, or before going live)

```
cd public
python -m http.server 8000
```
Open `http://localhost:8000/index.html` — `localhost` counts as a secure
context, so `crypto.subtle` (used for hashing) works. Once some data is
uploaded to the bucket, test with 2–3 real names/certificate numbers pulled
from `certificate_manifest.csv`, plus a real phone number from the xlsx.

**Test `/gen` locally too** (`http://localhost:8000/gen/index.html`):
generate a throwaway test certificate and confirm the downloaded JPG looks
right. It's a self-contained page — no bucket calls involved.

**After deploying**, re-run the same search tests against the live
`https://<user>.github.io/<repo>/` URL, not just localhost — a CORS
misconfiguration can pass locally (different origin, not actually exercised)
while silently failing every `fetch()` in production.

## 9. Known limitations

- **Sequential certificate numbers remain enumerable in principle.** The SALT
  ships in public client-side JS — it's not a real secret. Since
  `BAATEM25-XXXXX` is a small, sequential space, a determined actor could
  compute the hash for every possible certificate number and fetch each
  `index/by-certno/*.json` directly, bypassing the search UI. Disabling
  bucket **list** access (§6) stops casual browsing, but not a targeted
  brute-force script. This is an inherent limit of hash-obfuscation without a
  real secret/backend — acceptable for a closed-audience "simple and correct"
  tool, but worth knowing.
- Certificates generated via `/gen` are not searchable on the site — it only
  produces a downloadable image (see §5). To make a `/gen`-generated
  certificate searchable, it needs to be added to the bucket separately.
- Canvas-rendered certificates from `/gen` are a close, not pixel-perfect,
  match to the original GDI+-rendered batch.
- Phone matching uses "last 10 digits" rather than a strict "exactly 10
  digits" rule, to tolerate country-code prefixes in real data.
