const normalizeBoolean = (value: unknown): boolean => {
  if (typeof value === "string") {
    return value.trim().toLowerCase() === "true";
  }
  if (typeof value === "boolean") {
    return value;
  }
  return false;
};

export const SWFT_WORKSPACE_ENABLED = normalizeBoolean(import.meta.env.VITE_ENABLE_SWFT_WORKSPACE);
