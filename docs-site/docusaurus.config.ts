import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'ARIA Docs',
  tagline: 'Ask. Reason. Illuminate. Act.',
  url: 'https://docs.aria.localhost',
  baseUrl: '/',
  organizationName: 'b2metric',
  projectName: 'aria',
  onBrokenLinks: 'warn',
  markdown: {hooks: {onBrokenMarkdownLinks: 'warn'}},
  i18n: {defaultLocale: 'en', locales: ['en']},
  presets: [
    [
      'classic',
      {
        docs: false,
        blog: false,
        theme: {customCss: './src/css/custom.css'},
      } satisfies Preset.Options,
    ],
  ],
  plugins: [
    [
      '@docusaurus/plugin-content-docs',
      {
        id: 'developers',
        path: 'developers',
        routeBasePath: 'developers',
        sidebarPath: './sidebars.developers.ts',
      },
    ],
    [
      '@docusaurus/plugin-content-docs',
      {
        id: 'guide',
        path: 'guide',
        routeBasePath: 'guide',
        sidebarPath: './sidebars.guide.ts',
      },
    ],
  ],
  themeConfig: {
    navbar: {
      title: 'ARIA',
      items: [
        {type: 'docSidebar', sidebarId: 'developersSidebar', docsPluginId: 'developers', position: 'left', label: 'Developers'},
        {type: 'docSidebar', sidebarId: 'guideSidebar', docsPluginId: 'guide', position: 'left', label: 'Guide'},
        {href: 'pathname:///api.html', label: 'API Reference', position: 'right'},
      ],
    },
    footer: {
      style: 'dark',
      copyright: 'B2Metric — ARIA. Ask. Reason. Illuminate. Act.',
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
