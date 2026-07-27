export const NOT_FOUND_MESSAGE = "I don't have information about that.";

const LEGACY_NOT_FOUND = "I couldn't find this in the document.";

export function isNotFoundAnswer(content) {
  if (!content) return false;
  const normalized = content.trim().toLowerCase();
  return (
    normalized === NOT_FOUND_MESSAGE.toLowerCase() ||
    normalized === LEGACY_NOT_FOUND.toLowerCase()
  );
}

export function formatAssistantAnswer(content) {
  if (isNotFoundAnswer(content)) return NOT_FOUND_MESSAGE;
  return content;
}
