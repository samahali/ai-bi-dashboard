import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link, useNavigate } from 'react-router-dom'
import { UserPlus, BrainCircuit } from 'lucide-react'
import toast from 'react-hot-toast'
import { AxiosError } from 'axios'
import { authService } from '@/services/authService'
import { useAuthStore } from '@/store/auth.store'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import Card from '@/components/ui/Card'

const schema = z.object({
  username:   z.string().min(3, 'Min 3 characters').max(50).regex(/^[a-zA-Z0-9_]+$/, 'Letters, numbers & underscores only'),
  email:      z.string().email('Invalid email address'),
  password:   z.string().min(8, 'Min 8 characters')
                .regex(/[A-Z]/, 'Must include an uppercase letter')
                .regex(/[0-9]/, 'Must include a number'),
  first_name: z.string().optional(),
  last_name:  z.string().optional(),
})
type FormData = z.infer<typeof schema>

export default function RegisterPage() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const onSubmit = async (data: FormData) => {
    try {
      const res = await authService.register(data)
      setAuth(res.user)
      toast.success('Welcome! Your account is ready.')
      navigate('/dashboard')
    } catch (error) {
      const axiosError = error as AxiosError<{ detail: string | Array<{msg: string, loc: string[]}> }>
      const errorData = axiosError.response?.data

      if (typeof errorData?.detail === 'string') {
        toast.error(errorData.detail)
      } else if (Array.isArray(errorData?.detail)) {
        const firstError = errorData.detail[0]
        toast.error(firstError?.msg || 'Registration failed')
      } else {
        toast.error('Registration failed. Please check your information.')
      }
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface px-4 py-10">
      <div className="w-full max-w-sm">
        {/* Brand */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-accent/10 mb-4">
            <BrainCircuit size={24} className="text-accent" />
          </div>
          <h1 className="text-2xl font-semibold text-[#1f2328]">Create Account</h1>
          <p className="text-sm text-muted mt-1">Start analyzing your data with AI</p>
        </div>

        <Card>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <Input label="First Name" placeholder="John" {...register('first_name')} required={false} />
              <Input label="Last Name"  placeholder="Doe"  {...register('last_name')} required={false} />
            </div>
            <Input label="Username"  placeholder="john_doe"         error={errors.username?.message}  {...register('username')} required />
            <Input label="Email"     type="email" placeholder="john@example.com" error={errors.email?.message} {...register('email')} required />
            <Input label="Password"  type="password" placeholder="Min 8 chars, 1 uppercase, 1 number" error={errors.password?.message} {...register('password')} required />
            <Button type="submit" loading={isSubmitting} className="w-full">
              <UserPlus size={15} />
              Create Account
            </Button>
          </form>
        </Card>

        <p className="text-center text-sm text-muted mt-4">
          Already have an account?{' '}
          <Link to="/login" className="text-accent hover:underline font-medium">Sign in</Link>
        </p>
      </div>
    </div>
  )
}
