function parseJson(text) {
  let candidate = text.trim();
  for (let i = 0; i < 3; i++) {
    try {
      return JSON.parse(candidate);
    } catch {
      candidate += "}";
    }
  }
  return null;
}