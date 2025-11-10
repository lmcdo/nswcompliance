/**
 * Water Rights MVP - Login Page
 * Professional login with value proposition
 */

'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import Link from 'next/link';
import {
  Droplet,
  Shield,
  TrendingUp,
  Bell,
  CheckCircle2,
  ArrowRight,
  Building2,
} from 'lucide-react';

export default function LoginPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-600 via-cyan-600 to-teal-600 flex items-center justify-center p-4">
      <div className="w-full max-w-6xl grid grid-cols-1 lg:grid-cols-2 gap-8 items-center">
        {/* Left Column - Branding & Value Props */}
        <div className="text-white space-y-8">
          {/* Logo & Title */}
          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="p-3 rounded-xl bg-white/20 backdrop-blur-sm">
                <Droplet className="h-10 w-10 text-white" />
              </div>
              <div>
                <h1 className="text-4xl font-bold">WaterRight</h1>
                <p className="text-blue-100 text-lg">Water Allocation Management</p>
              </div>
            </div>
            <p className="text-xl text-blue-50">
              Real-time water allocation tracking and compliance management for Australian farmers
            </p>
          </div>

          {/* Key Features */}
          <div className="space-y-4">
            <h2 className="text-2xl font-bold mb-4">Why WaterRight?</h2>

            <div className="flex items-start gap-3">
              <div className="p-2 rounded-lg bg-white/20 backdrop-blur-sm mt-1">
                <TrendingUp className="h-5 w-5" />
              </div>
              <div>
                <h3 className="font-semibold text-lg">Real-Time Allocation Tracking</h3>
                <p className="text-blue-100">
                  Know exactly how much water you have available across all entitlements. Updated
                  automatically with every allocation announcement.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="p-2 rounded-lg bg-white/20 backdrop-blur-sm mt-1">
                <Shield className="h-5 w-5" />
              </div>
              <div>
                <h3 className="font-semibold text-lg">Compliance Monitoring</h3>
                <p className="text-blue-100">
                  Avoid penalties up to $264,000. Get warned BEFORE you exceed allocation limits,
                  not after.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="p-2 rounded-lg bg-white/20 backdrop-blur-sm mt-1">
                <Bell className="h-5 w-5" />
              </div>
              <div>
                <h3 className="font-semibold text-lg">Instant Supplementary Alerts</h3>
                <p className="text-blue-100">
                  Never miss a supplementary flow event. Get SMS alerts the moment access is
                  declared with countdown timers.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="p-2 rounded-lg bg-white/20 backdrop-blur-sm mt-1">
                <CheckCircle2 className="h-5 w-5" />
              </div>
              <div>
                <h3 className="font-semibold text-lg">Automated Usage Tracking</h3>
                <p className="text-blue-100">
                  Integrate with Observant, Goanna Ag, and other telemetry providers. No more
                  manual meter readings.
                </p>
              </div>
            </div>
          </div>

          {/* Social Proof */}
          <div className="p-4 rounded-xl bg-white/10 backdrop-blur-sm border border-white/20">
            <p className="text-sm font-semibold mb-2">Trusted by farmers across NSW</p>
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="bg-white/20 text-white border-white/30">
                Murrumbidgee
              </Badge>
              <Badge variant="secondary" className="bg-white/20 text-white border-white/30">
                Murray
              </Badge>
              <Badge variant="secondary" className="bg-white/20 text-white border-white/30">
                Lachlan
              </Badge>
            </div>
          </div>
        </div>

        {/* Right Column - Login Form */}
        <div className="flex flex-col gap-6">
          {/* Login Card */}
          <Card className="w-full">
            <CardHeader>
              <CardTitle className="text-2xl">Sign In to Your Account</CardTitle>
              <CardDescription>Enter your credentials to access your water dashboard</CardDescription>
            </CardHeader>
            <CardContent>
              <form className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="email">Email Address</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="john.murphy@glenviewfarms.com.au"
                    className="h-11"
                  />
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="password">Password</Label>
                    <Link href="#" className="text-sm text-blue-600 hover:underline">
                      Forgot password?
                    </Link>
                  </div>
                  <Input id="password" type="password" className="h-11" />
                </div>

                <Link href="/water-demo" className="block">
                  <Button variant="default" size="lg" className="w-full">
                    Sign In
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </Link>

                <div className="relative">
                  <div className="absolute inset-0 flex items-center">
                    <span className="w-full border-t" />
                  </div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-white px-2 text-muted-foreground">Or</span>
                  </div>
                </div>

                <Button variant="outline" size="lg" className="w-full">
                  <Building2 className="mr-2 h-4 w-4" />
                  Sign in with Murrumbidgee Irrigation
                </Button>
              </form>
            </CardContent>
          </Card>

          {/* Sign Up CTA */}
          <Card className="bg-gradient-to-r from-blue-50 to-cyan-50 border-blue-200">
            <CardContent className="pt-6">
              <div className="text-center">
                <p className="font-semibold mb-2">Don't have an account?</p>
                <p className="text-sm text-muted-foreground mb-4">
                  Start your 30-day free trial today. No credit card required.
                </p>
                <Button variant="outline" className="w-full">
                  Create Free Account
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Pricing Hint */}
          <div className="text-center text-sm text-white">
            <p className="mb-1">Starting at $75/month</p>
            <p className="text-blue-100">
              Save thousands in compliance costs and avoid penalties
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
