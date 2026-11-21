import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { expect, it, vi } from 'vitest'

import { FileDropzone } from './FileDropzone'

it('validates staged files, keeps a rejected upload for retry, and clears it on receipt', async () => {
  const onUpload = vi.fn().mockResolvedValueOnce(false).mockResolvedValueOnce(true)
  render(<FileDropzone title="Bank statements" description="Includes UPI." disabled={false} uploading={false} onUpload={onUpload} />)
  const picker = screen.getByLabelText('Choose file for Bank statements')
  for (const [file, message] of [
    [new File(['header'], 'not-a-csv.txt'), 'Choose a CSV file.'],
    [new File([], 'empty.csv'), 'Choose a file that contains records.'],
    [new File([new Uint8Array(2 * 1024 * 1024 + 1)], 'large.csv'), 'Choose a file up to 2 MiB.'],
  ] as const) {
    fireEvent.change(picker, { target: { files: [file] } })
    expect(screen.getByRole('alert')).toHaveTextContent(message)
  }
  const sample = new File(['external_ref\nref-1'], 'statement.csv', { type: 'text/csv' })
  fireEvent.change(picker, { target: { files: [sample] } })
  expect(onUpload).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Upload selected file' }))
  await waitFor(() => expect(onUpload).toHaveBeenCalledWith(sample))
  expect(screen.getByText('statement.csv')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Upload selected file' }))
  await waitFor(() => expect(screen.queryByText('statement.csv')).not.toBeInTheDocument())
})
