// Shared data helpers: level list, concepts, base-path aware URLs.

export const BASE = import.meta.env.BASE_URL.replace(/\/?$/, '/');

/** Build a URL under the site base: u('levels/zygpt/') -> /tisc-2026/levels/zygpt/ */
export function u(path = ''): string {
  return BASE + path.replace(/^\//, '');
}

export interface LevelMeta {
  level: number;
  title: string;
  slug: string;
  category: string;
  difficulty?: string;
  flag: string;
  summary: string;
  tldr: string[];
  techniques: string[];
  learned: string[];
  workings?: string;
  time?: string;
  assist?: string;
  url: string;
}

const levelModules = import.meta.glob<{ frontmatter: Omit<LevelMeta, 'url'> }>('../pages/levels/*.md', {
  eager: true,
});

export const levels: LevelMeta[] = Object.values(levelModules)
  .map((m) => ({ ...m.frontmatter, url: u(`levels/${m.frontmatter.slug}/`) }))
  .sort((a, b) => a.level - b.level);

export function levelBySlug(slug: string) {
  return levels.find((l) => l.slug === slug);
}

export function neighbours(slug: string) {
  const i = levels.findIndex((l) => l.slug === slug);
  return { prev: i > 0 ? levels[i - 1] : undefined, next: i >= 0 && i < levels.length - 1 ? levels[i + 1] : undefined };
}

export interface Concept {
  id: string;
  term: string;
  group: string;
  short: string;
  long: string;
}

const conceptModules = import.meta.glob<{ default: Concept[] }>('../data/concepts/*.json', { eager: true });

const seen = new Set<string>();
export const concepts: Concept[] = Object.values(conceptModules)
  .flatMap((m) => m.default)
  .filter((c) => (seen.has(c.id) ? false : (seen.add(c.id), true)))
  .sort((a, b) => a.term.localeCompare(b.term));

export const conceptById = new Map(concepts.map((c) => [c.id, c]));

export const GROUP_ORDER = ['AI / ML', 'Crypto', 'Reverse engineering', 'Pwn', 'Forensics', 'Web', 'Method'];

/** Levels whose technique list includes a concept id. */
export function levelsUsing(id: string) {
  return levels.filter((l) => l.techniques?.includes(id));
}

export const pad = (n: number) => String(n).padStart(2, '0');

/** Human-led from L4 onwards; the early levels were AI-assisted. */
export function assistKind(l: Pick<LevelMeta, 'assist' | 'level'>): 'human' | 'ai' {
  if (l.assist) return /human/i.test(l.assist) ? 'human' : 'ai';
  return l.level >= 4 ? 'human' : 'ai';
}

export interface PostmortemMeta {
  title: string;
  challenge: string;
  category?: string;
  status?: string;
  summary: string;
  url: string;
  slug: string;
}

const pmModules = import.meta.glob<{ frontmatter: Omit<PostmortemMeta, 'url' | 'slug'> }>('../pages/postmortems/*.md', {
  eager: true,
});

export const postmortems: PostmortemMeta[] = Object.entries(pmModules).map(([path, m]) => {
  const slug = path.split('/').pop()!.replace(/\.md$/, '');
  return { ...m.frontmatter, slug, url: u(`postmortems/${slug}/`) };
});
