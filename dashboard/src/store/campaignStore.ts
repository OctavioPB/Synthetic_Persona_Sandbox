import { create } from 'zustand'

export type StimulusType = 'ad_copy' | 'price_change' | 'promo'

export interface AdCopyStimulus {
  type: 'ad_copy'
  headline: string
  body_copy: string
  cta: string
}

export interface PriceChangeStimulus {
  type: 'price_change'
  product_name: string
  original_price: number
  new_price: number
}

export interface PromoStimulus {
  type: 'promo'
  promo_code: string
  discount_value: number
  discount_type: 'percent' | 'fixed'
  expiry_days?: number
}

export type StimulusPayload = AdCopyStimulus | PriceChangeStimulus | PromoStimulus

export interface VariantSpec {
  name: string
  stimulus: StimulusPayload
}

export interface RunResult {
  variantIndex: number
  variantName: string
  runId: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'error'
  conversionScore: number | null
  verbatimResponse: string | null
  sentiment: string | null
  latencyMs: number | null
}

interface CampaignForm {
  name: string
  description: string
  segmentId: string
  segmentName: string
  variants: VariantSpec[]
}

const emptyForm: CampaignForm = {
  name: '',
  description: '',
  segmentId: '',
  segmentName: '',
  variants: [],
}

interface CampaignStore {
  form: CampaignForm
  setFormField: (field: keyof Omit<CampaignForm, 'variants'>, value: string) => void
  addVariant: (v: VariantSpec) => void
  removeVariant: (i: number) => void
  resetForm: () => void

  campaignResults: RunResult[]
  setCampaignResults: (results: RunResult[]) => void
}

export const useCampaignStore = create<CampaignStore>((set) => ({
  form: { ...emptyForm },

  setFormField: (field, value) =>
    set((s) => ({ form: { ...s.form, [field]: value } })),

  addVariant: (v) =>
    set((s) => ({ form: { ...s.form, variants: [...s.form.variants, v] } })),

  removeVariant: (i) =>
    set((s) => ({
      form: { ...s.form, variants: s.form.variants.filter((_, idx) => idx !== i) },
    })),

  resetForm: () => set({ form: { ...emptyForm }, campaignResults: [] }),

  campaignResults: [],
  setCampaignResults: (results) => set({ campaignResults: results }),
}))
