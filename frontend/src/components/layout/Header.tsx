import { LogOut, User, Menu, Settings, Globe } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/stores/authStore'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import { useUIStore } from '@/stores/uiStore'
import { updateProfile } from '@/api/auth'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'

interface HeaderProps {
  onNavigate: (route: string) => void
  onLogout: () => void
}

export function Header({ onNavigate, onLogout }: HeaderProps) {
  const { t, i18n } = useTranslation()
  const { user, updateUser } = useAuthStore()
  const { currentWorkspace } = useWorkspaceStore()
  const { toggleSidebar } = useUIStore()

  const initials = user?.name
    ? user.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    : 'U'

  const currentLanguage = i18n.language as 'en' | 'ru'

  const handleLanguageChange = async (lang: 'en' | 'ru') => {
    try {
      await updateProfile({ preferred_language: lang })
      updateUser({ preferred_language: lang })
    } catch {
      // Still update locally even if API fails
      i18n.changeLanguage(lang)
    }
  }

  return (
    <header className="sticky top-0 z-30 h-16 bg-background border-b px-6 flex items-center justify-between">
      {/* Left side */}
      <div className="flex items-center gap-4">
        {/* Mobile menu button */}
        <Button
          variant="ghost"
          size="icon"
          className="lg:hidden"
          onClick={toggleSidebar}
        >
          <Menu className="h-5 w-5" />
        </Button>

        {currentWorkspace && (
          <div className="flex items-center gap-2">
            <span className="font-medium hidden sm:block">{currentWorkspace.name}</span>
            <Badge variant="secondary">Free</Badge>
          </div>
        )}
      </div>

      {/* Right side */}
      <div className="flex items-center gap-2">
        {/* Language switcher */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" title={t('header.language')}>
              <Globe className="h-5 w-5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem
              onClick={() => handleLanguageChange('ru')}
              className="cursor-pointer"
            >
              Русский {currentLanguage === 'ru' && '✓'}
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => handleLanguageChange('en')}
              className="cursor-pointer"
            >
              English {currentLanguage === 'en' && '✓'}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* User menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="flex items-center gap-2">
              <Avatar className="h-8 w-8">
                <AvatarFallback className="text-sm">{initials}</AvatarFallback>
              </Avatar>
              <span className="hidden md:block text-sm">
                {user?.name}
              </span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>
              <div className="flex flex-col">
                <span>{user?.name}</span>
                <span className="text-sm font-normal text-muted-foreground">
                  {user?.email}
                </span>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={() => onNavigate('profile')}
              className="cursor-pointer"
            >
              <User className="mr-2 h-4 w-4" />
              {t('header.profile')}
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => onNavigate('api-keys')}
              className="cursor-pointer"
            >
              <Settings className="mr-2 h-4 w-4" />
              {t('nav.apiKeys')}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onClick={onLogout}
              className="text-destructive cursor-pointer"
            >
              <LogOut className="mr-2 h-4 w-4" />
              {t('header.logout')}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
