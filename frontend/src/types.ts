export type Category =
  | 'food'
  | 'transport'
  | 'entertainment'
  | 'shopping'
  | 'health'
  | 'subscriptions'
  | 'housing'
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
  'food', 'transport', 'entertainment', 'shopping', 'health', 'subscriptions', 'housing', 'other',
]

export const CATEGORY_LABELS: Record<Category, string> = {
  food: 'Food',
  transport: 'Transport',
  entertainment: 'Entertainment',
  shopping: 'Shopping',
  health: 'Health',
  subscriptions: 'Subscriptions',
  housing: 'Housing',
  other: 'Other',
}

export const CATEGORY_ICONS: Record<Category, string> = {
  food: '🍕',
  transport: '🚗',
  entertainment: '🎮',
  shopping: '🛒',
  health: '💊',
  subscriptions: '📱',
  housing: '🏠',
  other: '📦',
}

export const CATEGORY_COLORS: Record<Category, string> = {
  food: '#6366f1',
  transport: '#f59e0b',
  entertainment: '#ec4899',
  shopping: '#14b8a6',
  health: '#22c55e',
  subscriptions: '#8b5cf6',
  housing: '#f97316',
  other: '#94a3b8',
}

// ---------- Budget plans ----------

export interface AllocationItem {
  category: Category
  amount: number
  is_fixed: boolean
}

export interface PlanMonthView {
  month_index: number
  year: number
  month: number
  allocations: AllocationItem[]
  unallocated: number
}

export type FundingStrategy = 'spread' | 'absorb'

export interface PlanEvent {
  id: string
  name: string
  category: Category
  amount: number
  month_index: number
  funding: FundingStrategy
}

export interface PlanSummary {
  monthly_income: number
  fixed_total: number
  monthly_savings: number
  discretionary: number
  unallocated: number
}

export type FundingMode = 'income' | 'pot'

export interface Plan {
  id: string
  user_id: string
  start_date: string
  horizon_months: number
  savings_goal: number
  funding_mode: FundingMode
  total_funds: number | null
  summary: PlanSummary
  months: PlanMonthView[]
  events: PlanEvent[]
}

export interface PlanPreview {
  summary: PlanSummary
  allocations: AllocationItem[]
}

export interface PlanCreatePayload {
  funding_mode: FundingMode
  monthly_income?: number
  total_funds?: number
  start_date: string
  horizon_months: number
  savings_goal: number
  fixed_expenses: Partial<Record<Category, number>>
  variable_estimates: Partial<Record<Category, number>>
}

export interface MonthCategoryActual {
  category: Category
  planned: number
  actual: number
  difference: number
}

export interface MonthAnalysis {
  month_index: number
  year: number
  month: number
  income_actual: number
  expenses_actual: number
  savings_actual: number
  savings_planned: number
  categories: MonthCategoryActual[]
  remaining_funds: number | null
  expected_remaining: number | null
}

export interface AnalysisInsights {
  going_well: string[]
  needs_attention: string[]
  suggestions: string[]
}

export interface PlanAnalysis {
  funding_mode: FundingMode
  months_analyzed: number
  months: MonthAnalysis[]
  consistently_over: Category[]
  consistently_under: Category[]
  insights: AnalysisInsights | null
  insights_note: string | null
}
