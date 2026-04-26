import DefaultTheme from "vitepress/theme";
import { h } from "vue";
import CustomFooter from "./CustomFooter.vue";
import "./custom.css";

export default {
  extends: DefaultTheme,
  Layout() {
    return h(DefaultTheme.Layout, null, {
      "layout-bottom": () => h(CustomFooter),
    });
  },
};
