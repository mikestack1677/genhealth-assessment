/// <reference types="vite/client" />
/// <reference types="vitest/globals" />

declare module "*.module.css" {
  const classes: Record<string, string>;
  export default classes;
}
