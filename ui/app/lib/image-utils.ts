/**
 * Utility functions for image validation and handling
 */

/**
 * Validates if a URL is a valid image URL
 * @param url The URL to validate
 * @returns boolean indicating if the URL is valid
 */
export const isValidImageUrl = (url: string): boolean => {
  try {
    const parsedUrl = new URL(url);
    const validImageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'];
    const pathname = parsedUrl.pathname.toLowerCase();
    
    return validImageExtensions.some(ext => pathname.endsWith(ext));
  } catch {
    return false;
  }
};

/**
 * Preloads an image to verify it can be loaded
 * @param url The image URL to preload
 * @returns Promise that resolves to true if the image loads successfully, false otherwise
 */
export const preloadImage = (url: string): Promise<boolean> => {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve(true);
    img.onerror = () => resolve(false);
    img.src = url;
  });
};

/**
 * Validates and preloads an image URL
 * @param url The image URL to validate and preload
 * @returns Promise that resolves to an object containing validation results
 */
export const validateImageUrl = async (url: string): Promise<{
  isValid: boolean;
  isLoadable: boolean;
  error?: string;
}> => {
  if (!url) {
    return {
      isValid: false,
      isLoadable: false,
      error: 'No image URL provided'
    };
  }

  if (!isValidImageUrl(url)) {
    return {
      isValid: false,
      isLoadable: false,
      error: 'Invalid image URL format'
    };
  }

  try {
    const isLoadable = await preloadImage(url);
    return {
      isValid: true,
      isLoadable,
      error: isLoadable ? undefined : 'Image failed to load'
    };
  } catch (error) {
    return {
      isValid: true,
      isLoadable: false,
      error: 'Error validating image URL'
    };
  }
}; 