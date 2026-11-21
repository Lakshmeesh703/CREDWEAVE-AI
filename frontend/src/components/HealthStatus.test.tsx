import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { HealthStatus } from './HealthStatus'

describe('HealthStatus', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('shows a friendly message when the API is unavailable', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('offline'))

    render(<HealthStatus />)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'The local API is unavailable.',
    )
  })
})
