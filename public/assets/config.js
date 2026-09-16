// Shared config + hashing/normalization helpers for the public search page
// (index.html) and the hidden admin page (gen/index.html). Both pages load
// this exact file via <script src>, so there is only one copy to keep in sync
// on the JS side.
//
// tools/bootstrap_bucket.py (Python, used to build the initial bucket
// contents) needs its OWN literal copy of SALT, since it can't import a .js
// file — see the "MUST match public/assets/config.js exactly" comment there.

// TODO before going live: replace with your own secret-ish value, then re-run
// tools/bootstrap_bucket.py and re-upload gcs_upload/ so the index files use
// the new SALT. Must be identical here and in tools/bootstrap_bucket.py.
const SALT = "s5nF3nbmO9rbo6azJFqnmXPBhuVaDVop";

// TODO confirm this is the final public bucket URL you want to use.
const BUCKET_BASE_URL = "https://storage.googleapis.com/certificate_baa";

// SubtleCrypto requires a "secure context" (HTTPS, or http://localhost for
// local testing) — both GitHub Pages and `python -m http.server` on
// localhost satisfy this, so no extra setup is needed either place.
async function sha256Hex(str) {
  const bytes = new TextEncoder().encode(str); // UTF-8 — must match Python's .encode("utf-8")
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function normalizeName(s) {
  return s.trim().toLowerCase().replace(/\s+/g, " ");
}

function normalizePhone(s) {
  // Digits only. Real-world entries sometimes include a leading country code
  // (e.g. "+91XXXXXXXXXX"), so we keep the last 10 digits rather than
  // requiring exactly 10 — this is applied identically here, in
  // tools/bootstrap_bucket.py, and in gen/index.html.
  const digits = s.replace(/\D+/g, "");
  return digits.length > 10 ? digits.slice(-10) : digits;
}

function normalizeEmail(s) {
  return s.trim().toLowerCase();
}

function normalizeCertNo(s) {
  return s.trim().toUpperCase();
}

const NORMALIZERS = {
  name: normalizeName,
  phone: normalizePhone,
  email: normalizeEmail,
  cert_no: normalizeCertNo,
};

// field -> index folder name (cert_no's folder is "certno", not "cert_no")
const INDEX_FOLDER = {
  name: "by-name",
  phone: "by-phone",
  email: "by-email",
  cert_no: "by-certno",
};

async function hashFor(field, rawValue) {
  const normalize = NORMALIZERS[field];
  return sha256Hex(SALT + normalize(rawValue));
}

function indexUrlFor(field, hash) {
  return `${BUCKET_BASE_URL}/index/${INDEX_FOLDER[field]}/${hash}.json`;
}

function fileUrlFor(relativePath) {
  return `${BUCKET_BASE_URL}/${relativePath}`;
}
