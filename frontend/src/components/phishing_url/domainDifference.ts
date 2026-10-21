/** Edit alignment preserves insertions/deletions and Unicode code points. */
export function domainDifference(actual: string, reference: string) {
  const a = Array.from(actual), b = Array.from(reference);
  // Recorded domains are bounded; refuse oversized untrusted report values.
  if (a.length > 253 || b.length > 253) return [];
  const d = Array.from({length: a.length + 1}, () => Array<number>(b.length + 1).fill(0));
  for (let i = 0; i <= a.length; i++) d[i][0] = i;
  for (let j = 0; j <= b.length; j++) d[0][j] = j;
  for (let i = 1; i <= a.length; i++) for (let j = 1; j <= b.length; j++)
    d[i][j] = Math.min(d[i-1][j]+1, d[i][j-1]+1, d[i-1][j-1]+(a[i-1] === b[j-1] ? 0 : 1));
  const rows: Array<{actual: string; reference: string; changed: boolean; actualPosition: number}> = [];
  let i = a.length, j = b.length;
  while (i || j) {
    if (i && j && d[i][j] === d[i-1][j-1] + (a[i-1] === b[j-1] ? 0 : 1)) {
      rows.push({actual:a[i-1], reference:b[j-1], changed:a[i-1] !== b[j-1], actualPosition:i}); i--; j--;
    } else if (i && d[i][j] === d[i-1][j]+1) {
      rows.push({actual:a[i-1], reference:'', changed:true, actualPosition:i}); i--;
    } else { rows.push({actual:'', reference:b[j-1], changed:true, actualPosition:i+1}); j--; }
  }
  return rows.reverse();
}

export const codePoint = (char: string) => char ? `U+${char.codePointAt(0)!.toString(16).toUpperCase().padStart(4,'0')}` : 'absent';
