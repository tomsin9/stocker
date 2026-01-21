// Application configuration
// This file centralizes app metadata that can be used across the application
// 
// Best practices:
// 1. Version comes from package.json (via import.meta.env or build-time injection)
// 2. Other metadata can be overridden via environment variables in .env files
// 3. All values have sensible defaults

// App metadata from environment variables (with fallbacks)
// These can be overridden via .env files (e.g., VITE_APP_VERSION=1.0.0)
// For version, prefer using package.json version via build-time injection
export const APP_VERSION = import.meta.env.VITE_APP_VERSION || import.meta.env.PACKAGE_VERSION || '0.0.0'
export const APP_NAME = import.meta.env.VITE_APP_NAME || 'Stocker'
export const APP_AUTHOR = import.meta.env.VITE_APP_AUTHOR || 'Tom Sin'
export const APP_AUTHOR_EMAIL = import.meta.env.VITE_APP_AUTHOR_EMAIL || 'contact@tomsinp.com'
export const APP_REPOSITORY = import.meta.env.VITE_APP_REPOSITORY || 'https://github.com/tomsin9/stocker'
export const APP_LICENSE = import.meta.env.VITE_APP_LICENSE || 'GNU AGPL v3'
export const APP_LICENSE_URL = import.meta.env.VITE_APP_LICENSE_URL || 'https://www.gnu.org/licenses/agpl-3.0.html'

// Export all app info as a single object for convenience
export const APP_INFO = {
  name: APP_NAME,
  version: APP_VERSION,
  author: APP_AUTHOR,
  authorEmail: APP_AUTHOR_EMAIL,
  repository: APP_REPOSITORY,
  license: APP_LICENSE,
  licenseUrl: APP_LICENSE_URL
}
