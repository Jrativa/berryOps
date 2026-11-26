import { useId, useState } from "react";
import { useTranslation } from "react-i18next";
import { motion } from "motion/react";
import { Eye, EyeOff } from "lucide-react";

import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { riseIn, stagger } from "@/shared/lib/motion";

interface LoginFormProps {
  isLoading: boolean;
  error: string | null;
  onSubmit: (username: string, password: string) => void;
}

export function LoginForm({ isLoading, error, onSubmit }: LoginFormProps) {
  const { t } = useTranslation();
  const errorId = useId();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = (e: React.SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault();
    onSubmit(username.trim(), password);
  };

  return (
    <motion.form
      variants={stagger}
      initial="hidden"
      animate="show"
      onSubmit={handleSubmit}
      className="flex flex-col gap-5"
      noValidate
    >
      <motion.div variants={riseIn} className="flex flex-col gap-2">
        <label htmlFor="username" className="text-sm font-medium text-midnight">
          {t("auth.username")}
        </label>
        <Input
          id="username"
          name="username"
          type="text"
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          autoFocus
          placeholder={t("auth.username.placeholder")}
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          disabled={isLoading}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : undefined}
          required
        />
      </motion.div>

      <motion.div variants={riseIn} className="flex flex-col gap-2">
        <label htmlFor="password" className="text-sm font-medium text-midnight">
          {t("auth.password")}
        </label>
        <div className="relative">
          <Input
            id="password"
            name="password"
            type={showPassword ? "text" : "password"}
            autoComplete="current-password"
            placeholder={t("auth.password.placeholder")}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={isLoading}
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? errorId : undefined}
            className="pr-12"
            required
          />
          <button
            type="button"
            onClick={() => setShowPassword((v) => !v)}
            aria-label={showPassword ? t("auth.password.hide") : t("auth.password.show")}
            aria-pressed={showPassword}
            className="absolute right-1.5 top-1/2 grid size-9 -translate-y-1/2 place-items-center rounded-full text-dusty transition-colors hover:bg-midnight/[0.06] hover:text-midnight"
          >
            {showPassword ? <EyeOff className="size-[18px]" /> : <Eye className="size-[18px]" />}
          </button>
        </div>
      </motion.div>

      {/* Región viva: el error se anuncia sin mover el foco */}
      <div aria-live="polite" id={errorId} className="min-h-5 -mt-1">
        {error && (
          <motion.p
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-sm text-danger"
          >
            {error}
          </motion.p>
        )}
      </div>

      <motion.div variants={riseIn}>
        <Button
          type="submit"
          size="lg"
          className="w-full"
          loading={isLoading}
          disabled={!username.trim() || !password}
        >
          {isLoading ? t("auth.signingin") : t("auth.signin")}
        </Button>
      </motion.div>
    </motion.form>
  );
}
