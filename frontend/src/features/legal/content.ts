// Standard, plain-language legal templates. Review with counsel before public
// launch and replace the [bracketed] placeholders with your entity details.
export interface LegalDoc {
  slug: string;
  title: string;
  updated: string;
  body: string;
}

const UPDATED = "July 14, 2026";
const CONTACT = "[support@your-domain.com]";
const ENTITY = "Personal AI (“we”, “us”)";

export const LEGAL: Record<string, LegalDoc> = {
  privacy: {
    slug: "privacy",
    title: "Privacy Policy",
    updated: UPDATED,
    body: `This Privacy Policy explains what ${ENTITY} collects, why, and your choices.

## Information we collect
- **Account information.** When you sign in with Google, we receive your name, email address, and profile picture. We do not receive or store your Google password.
- **Content you provide.** Your chats, prompts, uploaded files, projects, citations, and saved memories.
- **AI requests.** The messages and documents you send are forwarded to our AI provider(s) to generate responses.
- **Technical data.** Basic logs (timestamps, request paths, and security events) needed to operate and secure the service.

## How we use your data
- To provide the assistant: generate responses, retrieve relevant passages from your uploads (RAG), and remember durable facts you allow.
- To operate, secure, debug, and improve the service.
- To respond to support requests you send us.

## Uploaded files
Files you upload are stored in your private account, indexed for retrieval, and sent to the AI provider only when relevant to your request. You can delete any file at any time, which removes it and its embeddings.

## Cookies
We use a single essential, HTTP-only session cookie to keep you signed in. See our [Cookie Policy](/cookies).

## Google login
Authentication is handled by Google OAuth. Your use of Google sign-in is also governed by Google's privacy policy.

## AI providers
To generate responses we share your prompts and relevant content with third-party AI providers under their respective terms. We do not sell your data.

## Data retention
We keep your data until you delete it or delete your account. Deleting your account permanently removes your chats, files, memories, citations, and projects.

## Security
We hash secrets, enforce HTTPS in production, use HTTP-only session cookies, validate uploads, and log security events. No system is perfectly secure, but we work to protect your data.

## Your rights
You can access, export, or delete your data at any time from **Settings → Data controls**. Depending on your jurisdiction you may have additional rights (access, correction, erasure, portability).

## Account deletion
Delete your account from **Settings → Data controls → Delete account**. This is immediate and irreversible.

## Contact
Questions about privacy: ${CONTACT}.`,
  },

  terms: {
    slug: "terms",
    title: "Terms of Service",
    updated: UPDATED,
    body: `These Terms govern your use of ${ENTITY}. By using the service you agree to them.

## Acceptable use
You agree not to use the service to break the law, infringe others' rights, upload malware, attempt to disrupt or reverse-engineer the service, or generate harmful, abusive, or deceptive content.

## Your responsibilities
You are responsible for the content you submit and for keeping your account secure. You must have the rights to any files you upload.

## AI limitations
The assistant can be wrong, incomplete, or out of date. Do not rely on it for professional, legal, medical, or financial advice. Verify important information independently.

## Intellectual property
You retain ownership of the content you submit. We retain ownership of the software and service. You grant us the limited rights needed to operate the service (e.g., storing and processing your content to generate responses).

## Payments & refunds
The current offering is provided as-is. If paid plans are introduced, applicable pricing, billing, and refund terms will be presented at purchase.

## Account suspension
We may suspend or terminate accounts that violate these Terms or put the service or other users at risk.

## Limitation of liability
The service is provided “as is” without warranties. To the maximum extent permitted by law, we are not liable for indirect, incidental, or consequential damages arising from your use of the service.

## Governing law
These Terms are governed by the laws of [your jurisdiction], without regard to conflict-of-law rules.

## Changes to these Terms
We may update these Terms. Material changes will be reflected by the “Last updated” date, and continued use constitutes acceptance.

## Contact
Questions about these Terms: ${CONTACT}.`,
  },

  cookies: {
    slug: "cookies",
    title: "Cookie Policy",
    updated: UPDATED,
    body: `This Cookie Policy explains how ${ENTITY} uses cookies and similar technologies.

## What are cookies?
Cookies are small text files stored by your browser. We use the minimum necessary to run the service.

## Cookies we use
- **Essential (session).** A single HTTP-only cookie that keeps you signed in after Google login. The service cannot function without it.
- **Preferences.** Local browser storage remembers UI choices such as theme and your cookie-consent selection. This stays on your device.

We currently do **not** use advertising or third-party tracking cookies.

## Categories
- **Essential** — always on (required for sign-in).
- **Authentication** — provided by Google during login.
- **Preferences** — theme and consent, stored locally.
- **Analytics** — not currently used.

## Managing cookies
You can accept or reject non-essential storage from the consent banner, and clear cookies via your browser settings. Rejecting essential cookies will prevent sign-in.

## Contact
Questions about cookies: ${CONTACT}.`,
  },

  about: {
    slug: "about",
    title: "About Personal AI",
    updated: UPDATED,
    body: `**Personal AI** is a private research and writing assistant.

## What it is
A ChatGPT-style assistant built for focused research and thesis work — with your own documents, projects, and long-term memory.

## Why it exists
General chatbots forget your context and can't read your sources. Personal AI keeps your projects, remembers durable facts you allow, and answers grounded in the files you upload.

## Features
- Streaming responses with a live, account-derived model list
- Document understanding (PDF, Word, PowerPoint, Excel, text, code, and archives) with retrieval-augmented answers
- Vision for images and scanned PDFs
- Projects, selective long-term memory, and web search with sources
- A citation manager with BibTeX export
- Full data control: export and delete your data anytime

## Security
Login-gated via Google OAuth, HTTP-only session cookies, HTTPS in production, validated uploads, and security-event logging. See our [Privacy Policy](/privacy).

## Technologies
Flask + SQLAlchemy backend, React + TypeScript frontend, and modern LLM APIs.

## Mission
Make serious research assistance private, grounded, and genuinely useful.

## Roadmap
Email verification & password login, richer export, team projects, and expanded file support.

## Version
1.0 (Production readiness)`,
  },
};

export const LEGAL_LINKS = [
  { to: "/about", label: "About" },
  { to: "/privacy", label: "Privacy" },
  { to: "/terms", label: "Terms" },
  { to: "/cookies", label: "Cookies" },
  { to: "/support", label: "Contact" },
];
