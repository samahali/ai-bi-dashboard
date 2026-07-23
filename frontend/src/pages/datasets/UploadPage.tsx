import { useCallback, useState } from 'react'

import { useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import { UploadCloud, FileText, X, CheckCircle2 } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'

import { datasetService } from '@/services/datasetService'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import Card from '@/components/ui/Card'
import { cn, formatBytes } from '@/utils/helpers'

const ACCEPTED = { 'text/csv': ['.csv'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'], 'application/json': ['.json'] }
const MAX_SIZE = 100 * 1024 * 1024 // 100 MB

export default function UploadPage() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [name, setName]               = useState('')
  const [description, setDescription] = useState('')
  const [file, setFile]               = useState<File | null>(null)

  const onDrop = useCallback((accepted: File[]) => {
    const f = accepted[0]
    if (!f) return
    setFile(f)
    if (!name) setName(f.name.replace(/\.[^.]+$/, ''))
  }, [name])

  const { getRootProps, getInputProps, isDragActive, fileRejections } = useDropzone({
    onDrop,
    accept: ACCEPTED,
    maxFiles: 1,
    maxSize: MAX_SIZE,
  })

  const uploadMutation = useMutation({
    mutationFn: () => datasetService.upload(file!, { name, description }),
    onSuccess: (ds) => {
      toast.success('Dataset uploaded! Processing in background…')
      qc.invalidateQueries({ queryKey: ['datasets'] })
      navigate(`/datasets/${ds.id}`)
    },
    onError: () => toast.error('Upload failed. Please try again.'),
  })

  const rejectionMsg = fileRejections[0]?.errors[0]?.message

  return (
    <div className="max-w-xl mx-auto space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-[#1f2328]">Upload Dataset</h2>
        <p className="text-sm text-muted mt-1">Supports CSV, Excel (.xlsx), and JSON files up to 100 MB.</p>
      </div>

      {/* Drop zone */}
      <div
        {...getRootProps()}
        className={cn(
          'border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors',
          isDragActive  ? 'border-accent bg-accent/5' : 'border-border hover:border-accent/50 hover:bg-surface',
          file          ? 'border-green-400 bg-green-50' : ''
        )}
      >
        <input {...getInputProps()} />
        {file ? (
          <div className="flex flex-col items-center gap-2">
            <CheckCircle2 size={36} className="text-green-500" />
            <p className="text-sm font-medium text-[#1f2328]">{file.name}</p>
            <p className="text-xs text-muted">{formatBytes(file.size)}</p>
            <button
              onClick={(e) => { e.stopPropagation(); setFile(null) }}
              className="mt-1 flex items-center gap-1 text-xs text-muted hover:text-red-500 transition-colors"
            >
              <X size={12} /> Remove
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <UploadCloud size={36} className={isDragActive ? 'text-accent' : 'text-border'} />
            <div>
              <p className="text-sm font-medium text-[#1f2328]">
                {isDragActive ? 'Drop it here…' : 'Drag & drop your file here'}
              </p>
              <p className="text-xs text-muted mt-1">or click to browse · CSV, XLSX, JSON · Max 100 MB</p>
            </div>
          </div>
        )}
      </div>
      {rejectionMsg && <p className="text-xs text-red-500 -mt-4">{rejectionMsg}</p>}

      {/* Metadata */}
      <Card>
        <div className="space-y-4">
          <Input
            label="Dataset Name *"
            placeholder="e.g. Sales Data 2024"
            value={name}
            onChange={(e) => setName(e.target.value)}
            hint="Give it a clear, descriptive name."
          />
          <div>
            <label className="block text-sm font-medium text-[#1f2328] mb-1">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional — describe what this data contains"
              rows={3}
              className="w-full px-3 py-2 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent resize-none"
            />
          </div>
        </div>
      </Card>

      {/* Actions */}
      <div className="flex items-center gap-3">
        <Button
          disabled={!file || !name.trim()}
          loading={uploadMutation.isPending}
          onClick={() => uploadMutation.mutate()}
        >
          <FileText size={15} />
          Upload & Process
        </Button>
        <Button variant="secondary" onClick={() => navigate('/datasets')}>
          Cancel
        </Button>
      </div>
    </div>
  )
}
