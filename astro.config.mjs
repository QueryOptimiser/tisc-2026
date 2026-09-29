import { defineConfig } from 'astro/config';
import remarkDirective from 'remark-directive';
import { remarkCallouts, rehypeBaseLinks } from './src/lib/markdown.mjs';

// Served from GitHub Pages at https://queryoptimiser.github.io/tisc-2026/
const base = '/tisc-2026';

export default defineConfig({
  site: 'https://queryoptimiser.github.io',
  base,
  trailingSlash: 'always',
  markdown: {
    remarkPlugins: [remarkDirective, remarkCallouts],
    rehypePlugins: [[rehypeBaseLinks, { base }]],
    shikiConfig: {
      themes: { light: 'github-light', dark: 'github-dark-dimmed' },
      wrap: false,
    },
  },
});
