export function activityPath(activityId: number | string): string {
  return `/activities/${activityId}`;
}

export function racePath(slug: string): string {
  return `/race/${slug}`;
}

export function sportPath(prefix: 'run' | 'swim' | 'bike'): string {
  return `/${prefix}`;
}
