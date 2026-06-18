import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';
const sidebars: SidebarsConfig = {
  guideSidebar: [
    'intro',
    {type: 'category', label: 'Getting Started', items: ['why-aria', 'chat-flow', 'dashboard']},
    {type: 'category', label: 'Onboarding & Setup', items: ['onboarding', 'settings']},
    {type: 'category', label: 'Admin', items: ['admin-users', 'admin-vault-access', 'admin-tenant-config', 'admin-llm-config', 'admin-memory', 'admin-monitoring']},
    {type: 'category', label: 'Security & Governance', items: ['byok', 'cmek', 'vault-sync', 'row-limits', 'team-memory']},
    {type: 'category', label: 'Analytics & Artifacts', items: ['chart-types', 'data-exports']},
  ],
};
export default sidebars;
