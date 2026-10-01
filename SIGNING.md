# Code signing & notarization

The release workflow signs and notarizes **only when the secrets below exist**.
Until you add them, it still ships working *unsigned* builds — so nothing breaks
while you sort out certificates. Add the secrets under
**GitHub → repo → Settings → Secrets and variables → Actions → New repository secret**,
then push a tag to get signed binaries.

Base64 is just so binary files survive as text secrets. Encode with:
`base64 -i file` (macOS) or `base64 -w0 file` (Linux).

---

## macOS (Developer ID + notarization)

Requires a paid **Apple Developer account** ($99/yr). This makes the
"Apple couldn't verify" wall disappear for everyone.

### 1. Create a "Developer ID Application" certificate
In Xcode (Settings → Accounts → Manage Certificates → + → Developer ID
Application), or on the Apple Developer portal. Then in **Keychain Access**,
right-click the cert → **Export** as a `.p12` and set a password.

- `MACOS_CERT_P12_BASE64` — `base64 -i cert.p12`
- `MACOS_CERT_PASSWORD` — the password you set on export
- `MACOS_SIGN_IDENTITY` — the exact identity string, e.g.
  `Developer ID Application: Your Name (ABCDE12345)`.
  Find it with: `security find-identity -v -p codesigning`

### 2. Create an App Store Connect API key (for notarytool)
appstoreconnect.apple.com → Users and Access → **Integrations / Keys** →
generate a key with the **Developer** role. Download the `.p8` **once**.

- `AC_API_KEY_ID` — the key's ID (short string, e.g. `2X9R4HXF34`)
- `AC_API_ISSUER_ID` — the issuer UUID shown on the Keys page
- `AC_API_KEY_P8_BASE64` — `base64 -i AuthKey_XXXX.p8`

That's it — tag a release and the `.app` comes out signed, notarized, and
stapled, so a double-click just works.

> If notarization is rejected for *unsigned nested code*, it means a few bundled
> `.dylib`/`.so` files need signing before the app. The usual fix is to
> `codesign` each nested binary first, then the app. Shout if you hit this and
> I'll add the per-file signing loop.

---

## Windows (Authenticode)

> **Read this first.** Since June 2023, CAs no longer issue plain exportable
> `.pfx` files for new OV/EV code-signing certs — the private key must live on
> an HSM or hardware token, which a GitHub runner can't read. The `.pfx` path
> below only works if you already have an exportable cert (older, or a
> self-/internally-issued one). For a brand-new public cert, use **Azure Trusted
> Signing** instead (see below) — it's cloud-based, ~$10/mo, and built for CI.

### Option A — you have an exportable `.pfx`
- `WINDOWS_CERT_PFX_BASE64` — `base64 -w0 cert.pfx`
- `WINDOWS_CERT_PASSWORD` — the `.pfx` password

The workflow finds `signtool` and signs `MobGrind.exe` with a DigiCert
timestamp. Done.

### Option B — Azure Trusted Signing (recommended for a new cert)
Set up a Trusted Signing account + certificate profile in Azure, then replace
the Windows signing block with Microsoft's action
(`azure/trusted-signing-action`) and store the Azure credentials as secrets.
Say the word and I'll wire that variant in — it needs your Azure
endpoint, account name, and certificate profile name.

> A self-signed cert will sign the exe but **won't** clear SmartScreen for other
> people (their machine doesn't trust your CA). Only a cert from a trusted CA,
> or Azure Trusted Signing, removes the warning for everyone.
