import { defineConfig } from "vitepress";
import { copyFileSync } from "fs";
import { join } from "path";

export default defineConfig({
  title: "OpenMLR",
  description:
    "OpenMLR - AI-powered ML Research Agent that plans tasks, researches papers, writes drafts, and executes code",

  cleanUrls: true,

  head: [
    // Basic meta
    ["meta", { name: "author", content: "Anubhav Singh" }],
    ["meta", { name: "theme-color", content: "#3eaf7c" }],
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

  themeConfig: {
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
