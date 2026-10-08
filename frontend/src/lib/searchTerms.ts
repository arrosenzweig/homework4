/**
 * Query normalisation for the catalogue grid.
 *
 * This mirrors `backend/search_terms.py`. The chat assistant and the products
 * page are two doors into the same catalogue, and before this the two doors
 * disagreed: asking the assistant for "grey" returned 50 products, while
 * typing "grey" into the grid search returned none.
 *
 * Keep the two files in step. The backend version additionally rescues typos
 * against the live catalogue vocabulary; this one does the same against the
 * bundled snapshot.
 */

const MIN_TERM_LENGTH = 3

const KEEP_SHORT = new Set([
  'xs', 's', 'm', 'l', 'xl', 'xxl', 'tee', 'zip', 'art', 'law', 'cap', 'mom', 'dad',
])

const STOPWORDS = new Set([
  'a', 'an', 'the', 'and', 'or', 'of', 'for', 'with', 'in', 'on', 'to',
  'my', 'me', 'i', 'you', 'your', 'some', 'any', 'do', 'have', 'got',
  'want', 'need', 'looking', 'show', 'find', 'get', 'buy', 'something',
  'anything', 'please', 'thanks', 'that', 'this', 'these', 'those',
  'is', 'are', 'it', 'its', 'can', 'could', 'would', 'like', 'about',
])

const SYNONYMS: Record<string, string> = {
  grey: 'gray',
  colour: 'color',
  colours: 'colors',
  jumper: 'sweater',
  jumpers: 'sweater',
  pully: 'pullover',
  sweatshirts: 'sweatshirt',
  crew: 'crewneck',
  crewnecks: 'crewneck',
  hoody: 'hoodie',
  hoodys: 'hoodie',
  hoodies: 'hoodie',
  hooded: 'hoodie',
  tees: 'tee',
  tshirt: 't-shirt',
  tshirts: 't-shirt',
  teeshirt: 't-shirt',
  quarterzip: 'quarter-zip',
  halfzip: 'quarter-zip',
  zipup: 'full-zip',
  zipper: 'zip',
  coat: 'jacket',
  coats: 'jacket',
  jackets: 'jacket',
  fleeces: 'fleece',
  longsleeve: 'long-sleeve',
  longsleeves: 'long-sleeve',
  shirts: 'shirt',
  sweaters: 'sweater',
  pullovers: 'pullover',
  bulldogs: 'bulldog',
  colleges: 'college',
  gifts: 'gift',
  present: 'gift',
  presents: 'gift',
}

const PHRASES: Record<string, string> = {
  't shirt': 't-shirt',
  't shirts': 't-shirt',
  'tee shirt': 't-shirt',
  'quarter zip': 'quarter-zip',
  'half zip': 'quarter-zip',
  '1/4 zip': 'quarter-zip',
  'zip up': 'full-zip',
  'full zip': 'full-zip',
  'long sleeve': 'long-sleeve',
  'long sleeves': 'long-sleeve',
  'crew neck': 'crewneck',
  'mock neck': 'mockneck',
}

/** Levenshtein distance, capped — only used to rescue a short typo. */
function editDistance(a: string, b: string): number {
  if (Math.abs(a.length - b.length) > 2) return 99
  const prev = Array.from({ length: b.length + 1 }, (_, i) => i)
  const curr = new Array<number>(b.length + 1)
  for (let i = 1; i <= a.length; i++) {
    curr[0] = i
    for (let j = 1; j <= b.length; j++) {
      curr[j] = Math.min(
        prev[j] + 1,
        curr[j - 1] + 1,
        prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1),
      )
    }
    for (let j = 0; j <= b.length; j++) prev[j] = curr[j]
  }
  return prev[b.length]
}

function closestWord(term: string, vocabulary: Set<string>): string | null {
  if (term.length < 4) return null
  let best: string | null = null
  let bestDistance = 3
  for (const word of vocabulary) {
    if (Math.abs(word.length - term.length) > 2) continue
    const d = editDistance(term, word)
    if (d < bestDistance) {
      bestDistance = d
      best = word
      if (d === 1) break
    }
  }
  return best
}

/** Every word appearing in searchable catalogue text, for typo rescue. */
export function buildVocabulary(
  products: { name: string; description: string; category: string; tags: string[]; colors: string[] }[],
): Set<string> {
  const words = new Set<string>()
  for (const p of products) {
    const blob = [p.name, p.description, p.category, p.tags.join(' '), p.colors.join(' ')]
      .join(' ')
      .toLowerCase()
    for (const w of blob.match(/[a-z][a-z-]{2,}/g) ?? []) words.add(w)
  }
  return words
}

/** Turn a raw query into the terms the grid should actually match on. */
export function normalizeQuery(query: string, vocabulary?: Set<string>): string[] {
  let text = query.toLowerCase().trim()
  for (const [phrase, replacement] of Object.entries(PHRASES)) {
    text = text.split(phrase).join(replacement)
  }
  text = text.replace(/[^a-z0-9\-'\s]/g, ' ')

  const terms: string[] = []
  for (const raw of text.split(/\s+/)) {
    let term = raw.replace(/^[-']+|[-']+$/g, '')
    if (!term || STOPWORDS.has(term)) continue

    term = SYNONYMS[term] ?? term
    if (term.length < MIN_TERM_LENGTH && !KEEP_SHORT.has(term)) continue

    if (vocabulary && !vocabulary.has(term)) {
      const corrected = closestWord(term, vocabulary)
      if (corrected) term = corrected
    }
    if (!terms.includes(term)) terms.push(term)
  }
  return terms
}
