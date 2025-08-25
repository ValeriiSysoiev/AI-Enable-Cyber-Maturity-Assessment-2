import { redirect } from 'next/navigation';

/**
 * Redirect route for backward compatibility.
 * Legacy /assessments/new URLs will redirect to /new
 */
export default function AssessmentsNewRedirect() {
  redirect('/new');
}