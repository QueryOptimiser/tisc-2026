import { visit } from 'unist-util-visit';
import { h } from 'hastscript';

const KINDS = {
  concept: 'Concept',
  note: 'Note',
  hindsight: 'Hindsight',
  result: 'Result',
};

/** Turns :::concept / :::note / :::hindsight / :::result blocks into styled asides. */
export function remarkCallouts() {
  return (tree) => {
    visit(tree, (node) => {
      if (node.type === 'textDirective' || node.type === 'leafDirective') {
        // Unknown inline directives (e.g. a stray ":8080") are restored as plain text.
        if (node.type === 'textDirective') {
          node.type = 'text';
          node.value = ':' + node.name;
          delete node.children;
        }
        return;
      }
      if (node.type !== 'containerDirective' || !KINDS[node.name]) return;

      const attrs = node.attributes || {};
      const kind = node.name;
      const title = attrs.title || '';
      const id = attrs.id || '';

      const head = {
        type: 'paragraph',
        data: { hName: 'p', hProperties: { className: ['callout-head'] } },
        children: [
          {
            type: 'emphasis',
            data: { hName: 'span', hProperties: { className: ['callout-kind'] } },
            children: [{ type: 'text', value: KINDS[kind] }],
          },
          ...(title
            ? [{
                type: 'strong',
                data: { hName: 'span', hProperties: { className: ['callout-title'] } },
                children: [{ type: 'text', value: title }],
              }]
            : []),
        ],
      };

      const body = {
        type: 'blockquote',
        data: { hName: 'div', hProperties: { className: ['callout-body'] } },
        children: node.children,
      };

      const tail =
        kind === 'concept' && id
          ? [{
              type: 'paragraph',
              data: { hName: 'p', hProperties: { className: ['callout-more'] } },
              children: [{
                type: 'link',
                url: `/concepts/#${id}`,
                children: [{ type: 'text', value: 'In the glossary' }],
              }],
            }]
          : [];

      node.data = {
        hName: 'aside',
        hProperties: {
          className: ['callout', `callout-${kind}`],
          ...(id && kind === 'concept' ? { 'data-concept': id } : {}),
        },
      };
      node.children = [head, body, ...tail];
    });
  };
}

/** Prefixes root-relative links and images with the site base path. */
export function rehypeBaseLinks({ base = '' } = {}) {
  const fix = (url) =>
    typeof url === 'string' && url.startsWith('/') && !url.startsWith('//') && !url.startsWith(base + '/')
      ? base + url
      : url;
  return (tree) => {
    visit(tree, 'element', (node) => {
      if (node.tagName === 'a' && node.properties?.href) node.properties.href = fix(node.properties.href);
      if (node.tagName === 'img' && node.properties?.src) node.properties.src = fix(node.properties.src);
      // Wrap tables so they scroll inside their own box on phones.
      if (node.tagName === 'table' && !node.properties?.dataWrapped) {
        node.properties = { ...node.properties, dataWrapped: true };
      }
    });
    visit(tree, 'element', (node, index, parent) => {
      if (node.tagName === 'table' && parent && parent.tagName !== 'div') {
        parent.children[index] = h('div.table-wrap', [node]);
      }
    });
  };
}
