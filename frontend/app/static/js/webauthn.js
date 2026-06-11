/* BioPay WebAuthn / FIDO2 helper
   Handles base64url encoding/decoding and credential creation/assertion */

const WebAuthnHelper = {

  /* ── Base64url utilities ──────────────────────────────── */
  base64urlToBuffer(base64url) {
    const padded = base64url.replace(/-/g, '+').replace(/_/g, '/')
      + '='.repeat((4 - base64url.length % 4) % 4);
    const binary = atob(padded);
    const buffer = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) buffer[i] = binary.charCodeAt(i);
    return buffer.buffer;
  },

  bufferToBase64url(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (const b of bytes) binary += String.fromCharCode(b);
    return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
  },

  /* ── Decode py_webauthn options ───────────────────────── */
  decodeRegistrationOptions(options) {
    return {
      ...options,
      challenge: this.base64urlToBuffer(options.challenge),
      user: {
        ...options.user,
        id: this.base64urlToBuffer(options.user.id),
      },
      excludeCredentials: (options.excludeCredentials || []).map(c => ({
        ...c,
        id: this.base64urlToBuffer(c.id),
      })),
    };
  },

  decodeAuthenticationOptions(options) {
    return {
      ...options,
      challenge: this.base64urlToBuffer(options.challenge),
      allowCredentials: (options.allowCredentials || []).map(c => ({
        ...c,
        id: this.base64urlToBuffer(c.id),
      })),
    };
  },

  /* ── Encode credential for backend ───────────────────── */
  encodeRegistrationCredential(credential) {
    const response = credential.response;
    return {
      id: credential.id,
      rawId: this.bufferToBase64url(credential.rawId),
      type: credential.type,
      response: {
        clientDataJSON:    this.bufferToBase64url(response.clientDataJSON),
        attestationObject: this.bufferToBase64url(response.attestationObject),
        transports: credential.response.getTransports
          ? credential.response.getTransports()
          : [],
      },
    };
  },

  encodeAuthenticationCredential(credential) {
    const response = credential.response;
    return {
      id: credential.id,
      rawId: this.bufferToBase64url(credential.rawId),
      type: credential.type,
      response: {
        clientDataJSON:    this.bufferToBase64url(response.clientDataJSON),
        authenticatorData: this.bufferToBase64url(response.authenticatorData),
        signature:         this.bufferToBase64url(response.signature),
        userHandle: response.userHandle
          ? this.bufferToBase64url(response.userHandle)
          : null,
      },
    };
  },

  /* ── Check WebAuthn support ───────────────────────────── */
  isSupported() {
    return !!(window.PublicKeyCredential &&
              navigator.credentials &&
              navigator.credentials.create &&
              navigator.credentials.get);
  },

  async isPlatformAuthenticatorAvailable() {
    if (!this.isSupported()) return false;
    try {
      return await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
    } catch {
      return false;
    }
  },

  /* ── High-level register ──────────────────────────────── */
  async register(options) {
    if (!this.isSupported()) {
      throw new Error('WebAuthn is not supported in this browser.');
    }
    const decoded = this.decodeRegistrationOptions(options);
    const credential = await navigator.credentials.create({ publicKey: decoded });
    return this.encodeRegistrationCredential(credential);
  },

  /* ── High-level authenticate ──────────────────────────── */
  async authenticate(options) {
    if (!this.isSupported()) {
      throw new Error('WebAuthn is not supported in this browser.');
    }
    const decoded = this.decodeAuthenticationOptions(options);
    const credential = await navigator.credentials.get({ publicKey: decoded });
    return this.encodeAuthenticationCredential(credential);
  },

  /* ── Device fingerprint (for trusted device tracking) ── */
  getDeviceFingerprint() {
    const parts = [
      navigator.userAgent,
      navigator.language,
      screen.width + 'x' + screen.height,
      new Date().getTimezoneOffset(),
      navigator.hardwareConcurrency || 0,
    ];
    // Simple deterministic hash
    let hash = 0;
    const str = parts.join('|');
    for (let i = 0; i < str.length; i++) {
      hash = ((hash << 5) - hash) + str.charCodeAt(i);
      hash |= 0;
    }
    return Math.abs(hash).toString(36);
  },

  getDeviceName() {
    const ua = navigator.userAgent;
    if (/Windows/.test(ua))   return 'Windows Device';
    if (/Macintosh/.test(ua)) return 'Mac Device';
    if (/iPhone/.test(ua))    return 'iPhone';
    if (/iPad/.test(ua))      return 'iPad';
    if (/Android/.test(ua))   return 'Android Device';
    if (/Linux/.test(ua))     return 'Linux Device';
    return 'Unknown Device';
  },
};
