/**
 * ProductCard.tsx
 * 
 * A reusable component that displays product information in a card format.
 * This component is used by the display_product_card frontend tool.
 */

import React, { useEffect, useState } from 'react';
import { type DisplayProductCardParams } from '../lib/frontend-tools';
import { validateImageUrl } from '../lib/image-utils';

interface ProductCardProps {
  product: DisplayProductCardParams;
}

export const ProductCard: React.FC<ProductCardProps> = ({ product }) => {
  const [imageState, setImageState] = useState<{
    isValid: boolean;
    isLoadable: boolean;
    isLoading: boolean;
    error?: string;
  }>({
    isValid: false,
    isLoadable: false,
    isLoading: true
  });

  useEffect(() => {
    const validateImage = async () => {
      if (!product.image_url) {
        setImageState({
          isValid: false,
          isLoadable: false,
          isLoading: false,
          error: 'No image URL available'
        });
        return;
      }

      setImageState(prev => ({ ...prev, isLoading: true }));
      const result = await validateImageUrl(product.image_url);
      setImageState({
        ...result,
        isLoading: false
      });
    };

    validateImage();
  }, [product.image_url]);

  // Format price to 2 decimal places with currency symbol
  const formattedPrice = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD'
  }).format(product.price);

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden">
      <div className="flex">
        {/* Image container - smaller size on the left */}
        <div className="w-32 h-32 relative bg-gray-100">
          {imageState.isLoading ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-gray-900"></div>
            </div>
          ) : imageState.isValid && imageState.isLoadable ? (
            <img
              src={product.image_url}
              alt={product.product_name}
              className="w-full h-full object-cover"
              onError={() => setImageState(prev => ({ ...prev, isLoadable: false, error: 'Failed to load image' }))}
            />
          ) : (
            <div className="absolute inset-0 flex items-center justify-center bg-gray-200">
              <span className="text-gray-500 text-xs text-center px-2">
                {imageState.error || 'No image available'}
              </span>
            </div>
          )}
        </div>

        {/* Content container - on the right */}
        <div className="flex-1 p-4">
          <h3 className="text-lg font-semibold text-gray-800 mb-2">{product.product_name}</h3>
          {product.product_description && (
            <p className="text-gray-600 text-sm mb-3">{product.product_description}</p>
          )}
          <div className="flex justify-between items-center">
            <span className="text-xl font-bold text-gray-900">{formattedPrice}</span>
            {product.product_id && <span className="text-xs text-gray-500">ID: {product.product_id}</span>}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProductCard; 