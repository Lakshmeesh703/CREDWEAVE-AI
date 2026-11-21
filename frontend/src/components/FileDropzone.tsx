import { UploadCloud } from 'lucide-react'
import { useEffect, useId, useState } from 'react'

const maxFileBytes = 2 * 1024 * 1024
const recognizedColumns = new Set([
  'external_ref', 'transaction_date', 'amount_inr', 'direction', 'payment_channel', 'description', 'currency',
  'debit_inr', 'credit_inr', 'balance_inr', 'source_provider', 'counterparty_name', 'counterparty_type',
  'identifier_masked', 'invoice_no', 'issued_at', 'due_at', 'total_inr', 'status', 'monthly_payment_inr',
])

export function FileDropzone({ title, description, allowJson = false, disabled, uploading, onUpload }: {
  title: string
  description: string
  allowJson?: boolean
  disabled: boolean
  uploading: boolean
  onUpload: (file: File) => Promise<boolean>
}) {
  const id = useId()
  const [file, setFile] = useState<File>()
  const [columns, setColumns] = useState<string[]>([])
  const [error, setError] = useState('')
  const [dragging, setDragging] = useState(false)

  useEffect(() => {
    if (!file || !/\.csv$/i.test(file.name)) return
    const reader = new FileReader()
    reader.onload = () => {
      const header = String(reader.result).split(/\r?\n/, 1)[0]
      setColumns(header.split(',').map((column) => column.trim().replace(/^"|"$/g, '')).filter((column) => recognizedColumns.has(column)))
    }
    reader.readAsText(file.slice(0, 4096))
    return () => {
      reader.onload = null
      if (reader.readyState === FileReader.LOADING) reader.abort()
    }
  }, [file])

  function select(next: File | undefined) {
    if (!next || disabled) return
    setFile(undefined)
    setColumns([])
    if (!next.size) setError('Choose a file that contains records.')
    else if (next.size > maxFileBytes) setError('Choose a file up to 2 MiB.')
    else if (!(allowJson ? /\.(csv|json)$/i : /\.csv$/i).test(next.name)) setError(allowJson ? 'Choose a CSV or JSON file.' : 'Choose a CSV file.')
    else {
      setError('')
      setFile(next)
    }
  }

  return <section className={`min-w-0 rounded-xl border border-dashed p-4 ${dragging ? 'border-teal bg-emerald-50' : 'border-slate-300 bg-slate-50'}`}
    onDragOver={(event) => { event.preventDefault(); if (!disabled) setDragging(true) }}
    onDragLeave={() => setDragging(false)}
    onDrop={(event) => { event.preventDefault(); setDragging(false); select(event.dataTransfer.files[0]) }}>
    <UploadCloud className="text-teal" size={23} aria-hidden="true" />
    <h3 className="mt-2 font-bold">{title}</h3>
    <p id={id} className="mt-1 text-sm text-slate-600">{description} {allowJson ? 'CSV or JSON' : 'CSV'}, up to 2 MiB.</p>
    <input id={`${id}-file`} type="file" className="peer sr-only" disabled={disabled} aria-label={`Choose file for ${title}`}
      aria-describedby={id} accept={allowJson ? '.csv,.json' : '.csv'}
      onChange={(event) => { select(event.target.files?.[0]); event.target.value = '' }} />
    <label htmlFor={`${id}-file`} className={`cw-button-secondary mt-3 peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-teal ${disabled ? 'pointer-events-none opacity-50' : 'cursor-pointer'}`}>Choose file</label>
    {file && <div className="mt-3 space-y-2">
      <p className="break-all text-sm font-medium">{file.name} <span className="text-slate-600">({Math.max(1, Math.ceil(file.size / 1024))} KiB)</span></p>
      {columns.length > 0 && <details className="text-sm text-slate-600">
        <summary className="cursor-pointer font-semibold text-teal">Preview detected columns</summary>
        <p className="mt-1 break-words">{columns.join(', ')}</p>
      </details>}
      {uploading && <progress className="block w-full accent-teal" aria-label={`Uploading and validating ${title}`} />}
      <button type="button" className="cw-button" disabled={disabled} onClick={() => void onUpload(file).then((ok) => { if (ok) { setFile(undefined); setColumns([]) } })}>
        {uploading ? 'Validating…' : 'Upload selected file'}
      </button>
    </div>}
    {error && <p role="alert" className="mt-2 text-sm text-rose-800">{error}</p>}
  </section>
}
