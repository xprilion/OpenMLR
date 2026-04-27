import { defineConfig } from "vitepress";
import { copyFileSync, readFileSync } from "fs";
import { join, resolve } from "path";

const version = readFileSync(resolve(__dirname, "../../..", "VERSION"), "utf-8").trim();

export default defineConfig({
  title: "OpenMLR",
  description:
    "OpenMLR - AI-powered ML Research Agent that plans tasks, researches papers, writes drafts, and executes code",

  cleanUrls: true,

  head: [
    // Favicons
    ["link", { rel: "icon", type: "image/png", sizes: "32x32", href: "/favicon-32x32.png" }],
    ["link", { rel: "icon", type: "image/png", sizes: "16x16", href: "/favicon-16x16.png" }],
    ["link", { rel: "apple-touch-icon", sizes: "180x180", href: "/apple-touch-icon.png" }],
    ["link", { rel: "icon", href: "/favicon.ico" }],

    // Basic meta
    ["meta", { name: "author", content: "Anubhav Singh" }],
    ["meta", { name: "theme-color", content: "#3b82f6" }],
    [
      "meta",
      {
        name: "viewport",
        content: "width=device-width, initial-scale=1.0, viewport-fit=cover",
      },
    ],
    [
      "meta",
      {
        name: "keywords",
        content:
          "ML research, AI agent, research assistant, paper writing, arxiv, machine learning, OpenMLR",
      },
    ],
    ["link", { rel: "canonical", href: "https://openmlr.dev" }],
    ["link", { rel: "preconnect", href: "https://render.com" }],
    ["link", { rel: "preconnect", href: "https://www.herokucdn.com" }],
    ["link", { rel: "dns-prefetch", href: "https://render.com" }],
    ["link", { rel: "dns-prefetch", href: "https://www.herokucdn.com" }],

    // Open Graph
    ["meta", { property: "og:type", content: "website" }],
    ["meta", { property: "og:locale", content: "en_US" }],
    ["meta", { property: "og:site_name", content: "OpenMLR" }],
    ["meta", { property: "og:title", content: "OpenMLR - ML Research Agent" }],
    [
      "meta",
      {
        property: "og:description",
        content:
          "AI-powered ML Research Agent that plans tasks, researches papers, writes drafts, and executes code",
      },
    ],
    ["meta", { property: "og:url", content: "https://openmlr.dev" }],
    ["meta", { property: "og:image", content: "https://openmlr.dev/og-image.png" }],
    ["meta", { property: "og:image:width", content: "1200" }],
    ["meta", { property: "og:image:height", content: "630" }],

    // Twitter Card
    ["meta", { name: "twitter:card", content: "summary_large_image" }],
    ["meta", { name: "twitter:title", content: "OpenMLR - ML Research Agent" }],
    [
      "meta",
      {
        name: "twitter:description",
        content:
          "AI-powered ML Research Agent that plans tasks, researches papers, writes drafts, and executes code",
      },
    ],
    ["meta", { name: "twitter:image", content: "https://openmlr.dev/og-image.png" }],
  ],

  // Sitemap generation
  sitemap: {
    hostname: "https://openmlr.dev",
  },

  // Copy markdown files to dist for raw .md access
  async buildEnd(siteConfig) {
    const docs = [
      "index",
      "quickstart",
      "setup",
      "configuration",
      "modes",
      "tools",
      "compute",
      "projects",
      "architecture",
      "agent-harness",
      "api",
      "changelog",
    ];
    for (const doc of docs) {
      const src = join(siteConfig.srcDir, `${doc}.md`);
      const dest = join(siteConfig.outDir, `${doc}.md`);
      try {
        copyFileSync(src, dest);
      } catch (e) {
        console.warn(`Could not copy ${doc}.md:`, e);
      }
    }
  },

  vite: {
    define: {
      __APP_VERSION__: JSON.stringify(version),
    },
  },

  themeConfig: {
    logo: "/logo-64.png",
    nav: [
      { text: "Home", link: "/" },
      { text: "Setup", link: "/setup" },
      { text: "GitHub", link: "https://github.com/xprilion/OpenMLR" },
    ],
    sidebar: [
      {
        text: "Getting Started",
        items: [
          { text: "Overview", link: "/" },
          { text: "Quick Start", link: "/quickstart" },
          { text: "Setup & Installation", link: "/setup" },
          { text: "Configuration", link: "/configuration" },
        ],
      },
      {
        text: "Usage",
        items: [
          { text: "Projects & Workspaces", link: "/projects" },
          { text: "Modes (Plan / Execute)", link: "/modes" },
          { text: "Agent Tools", link: "/tools" },
          { text: "Compute Environments", link: "/compute" },
        ],
      },
      {
        text: "Reference",
        items: [
          { text: "Architecture", link: "/architecture" },
          { text: "Agent Harness", link: "/agent-harness" },
          { text: "REST API", link: "/api" },
          { text: "Changelog", link: "/changelog" },
        ],
      },
    ],
    socialLinks: [
      { icon: "github", link: "https://github.com/xprilion/OpenMLR" },
    ],
    // Footer is handled by custom component (CustomFooter.vue)
    // to support left/right layout with sitemap link
  },
});
