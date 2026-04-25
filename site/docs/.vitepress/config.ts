import { defineConfig } from "vitepress";

export default defineConfig({
  title: "OpenMLR",
  description: "ML Research Intern — Documentation",
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
          { text: "Setup & Installation", link: "/setup" },
          { text: "Configuration", link: "/configuration" },
        ],
      },
      {
        text: "Usage",
        items: [
          { text: "Modes (Plan / Research / Write)", link: "/modes" },
          { text: "Agent Tools", link: "/tools" },
        ],
      },
      {
        text: "Reference",
        items: [
          { text: "Architecture", link: "/architecture" },
          { text: "REST API", link: "/api" },
        ],
      },
    ],
    socialLinks: [
      { icon: "github", link: "https://github.com/xprilion/OpenMLR" },
    ],
    footer: {
      message: "Released under the MIT License.",
      copyright: "Copyright © 2026 Anubhav Singh",
    },
  },
});
