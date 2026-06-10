export type Category =
  | 'food'
  | 'transport'
  | 'entertainment'
  | 'shopping'
  | 'health'
  | 'subscriptions'
  | 'other'

export type TransactionType = 'income' | 'expense'

export interface Transaction {
  id: string
  user_id: string
  amount: number
  category: Category
  description: string
  date: string
  transaction_type: TransactionType
}

export interface ParsedTransaction {
  amount: number
  category: Category
  description: string
  date: string
  transaction_type: TransactionType
  confidence_note?: string
}

export interface Budget {
  id: string
  user_id: string
  category: Category
  monthly_limit: number
}

export interface BudgetProgress {
  category: Category
  monthly_limit: number
  spent: number
  percentage: number
  over_limit: boolean
}

export const CATEGORIES: Category[] = [
  'food', 'transport', 'entertainment', 'shopping', 'health', 'subscriptions', 'other',
]

export const CATEGORY_LABELS: Record<Category, string> = {
  food: 'Food',
  transport: 'Transport',
  entertainment: 'Entertainment',
  shopping: 'Shopping',
  health: 'Health',
  subscriptions: 'Subscriptions',
  other: 'Other',
}

export const CATEGORY_ICONS: Record<Category, string> = {
  food: '🍕',
  transport: '🚗',
  entertainment: '🎮',
  shopping: '🛒',
  health: '💊',
  subscriptions: '📱',
  other: '📦',
}

export const CATEGORY_COLORS: Record<Category, string> = {
  food: '#6366f1',
  transport: '#f59e0b',
  entertainment: '#ec4899',
  shopping: '#14b8a6',
  health: '#22c55e',
  subscriptions: '#8b5cf6',
  other: '#94a3b8',
}
