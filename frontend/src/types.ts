export type Size = 'XS' | 'S' | 'M' | 'L' | 'XL' | 'XXL'

export const SIZES: Size[] = ['XS', 'S', 'M', 'L', 'XL', 'XXL']

export interface Product {
  id: string
  name: string
  garmentType: string
  category: string
  description: string
  colors: string[]
  tags: string[]
  image: string
  price: number
  stock: Record<Size, number>
  totalStock: number
  /** Residential college or graduate school, when the product belongs to one. */
  collection?: string | null
  collectionType?: string | null
}

export const RESIDENTIAL_COLLEGE = 'Residential College'
export const GRADUATE_SCHOOL = 'Graduate & Professional School'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}
