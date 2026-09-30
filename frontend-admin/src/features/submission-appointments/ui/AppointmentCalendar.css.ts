import { style } from '@vanilla-extract/css'

export const calendar = style({
  display: 'grid',
  gap: 10,
  padding: 12,
  border: '1px solid var(--line)',
  borderRadius: 10,
  background: '#fff',
})

export const header = style({
  display: 'grid',
  gridTemplateColumns: '34px minmax(0, 1fr) 34px',
  alignItems: 'center',
  gap: 8,
})

export const monthTitle = style({
  color: 'var(--ink-800)',
  fontSize: 13,
  fontWeight: 700,
  textAlign: 'center',
  textTransform: 'capitalize',
})

export const navigationButton = style({
  display: 'grid',
  width: 34,
  height: 34,
  padding: 0,
  placeItems: 'center',
  border: '1px solid var(--line)',
  borderRadius: 8,
  background: '#fff',
  color: 'var(--ink-700)',
  fontSize: 20,
  lineHeight: 1,
  cursor: 'pointer',
  selectors: {
    '&:hover:not(:disabled)': {
      borderColor: 'var(--brand-100)',
      background: 'var(--brand-25)',
    },
    '&:disabled': {
      color: 'var(--ink-200)',
      cursor: 'not-allowed',
      opacity: 0.65,
    },
  },
})

export const weekdays = style({
  display: 'grid',
  gridTemplateColumns: 'repeat(7, minmax(0, 1fr))',
  gap: 4,
})

export const weekday = style({
  color: 'var(--ink-400)',
  fontSize: 10,
  fontWeight: 700,
  textAlign: 'center',
  textTransform: 'uppercase',
})

export const days = style({
  display: 'grid',
  gridTemplateColumns: 'repeat(7, minmax(0, 1fr))',
  gap: 4,
})

export const day = style({
  minWidth: 0,
  height: 38,
  padding: 0,
  border: '1px solid transparent',
  borderRadius: 8,
  background: 'transparent',
  color: 'var(--ink-300)',
  fontSize: 12,
  fontWeight: 600,
  cursor: 'not-allowed',
})

export const dayOutside = style({
  color: 'transparent',
})

export const dayAvailable = style({
  borderColor: 'var(--brand-100)',
  background: 'var(--brand-25)',
  color: 'var(--brand-700, #174f89)',
  cursor: 'pointer',
  selectors: {
    '&:hover': {
      borderColor: 'var(--brand-500)',
      background: '#eaf3ff',
    },
  },
})

export const daySelected = style({
  borderColor: 'var(--brand-500)',
  background: 'var(--brand-500)',
  color: '#fff',
  selectors: {
    '&:hover': {
      background: 'var(--brand-500)',
      color: '#fff',
    },
  },
})

export const dayFullyBooked = style({
  borderColor: 'var(--ink-100)',
  background: 'var(--ink-100)',
  color: 'var(--ink-400)',
  textDecoration: 'line-through',
})

export const legend = style({
  display: 'flex',
  flexWrap: 'wrap',
  gap: '6px 12px',
  color: 'var(--ink-400)',
  fontSize: 10.5,
})

export const legendItem = style({
  display: 'inline-flex',
  alignItems: 'center',
  gap: 5,
})

export const legendDot = style({
  width: 8,
  height: 8,
  border: '1px solid var(--line)',
  borderRadius: 3,
  background: 'var(--ink-100)',
})

export const legendDotAvailable = style({
  borderColor: 'var(--brand-100)',
  background: 'var(--brand-25)',
})

export const legendDotSelected = style({
  borderColor: 'var(--brand-500)',
  background: 'var(--brand-500)',
})

