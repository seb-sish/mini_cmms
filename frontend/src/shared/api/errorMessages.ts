import { ApiErrorCode } from "./apiError";
import { isApiError } from "./apiError";

const DEFAULT_ERROR_MESSAGE: string =
  "Не удалось выполнить операцию. Повторите попытку.";

const TECHNICAL_ERROR_MESSAGE: string =
  "Ошибка формирования запроса. Обратитесь к администратору системы.";

const ERROR_MESSAGES: Record<string, string> = {
  [ApiErrorCode.VALIDATION_ERROR]: "Проверьте правильность заполнения полей.",
  [ApiErrorCode.UNAUTHENTICATED]: "Сессия завершена. Войдите в систему снова.",
  [ApiErrorCode.INVALID_CREDENTIALS]: "Неверный логин или пароль.",
  [ApiErrorCode.ACCESS_DENIED]: "Недостаточно прав для выполнения операции.",
  [ApiErrorCode.NOT_FOUND]: "Запись не найдена или недоступна для вашей роли.",
  [ApiErrorCode.RATE_LIMITED]:
    "Слишком много неудачных попыток входа. Повторите позже.",
  [ApiErrorCode.VERSION_CONFLICT]:
    "Запись уже изменил другой пользователь. Данные обновлены, проверьте их и повторите действие.",
  [ApiErrorCode.PRECONDITION_REQUIRED]:
    "Не удалось подтвердить версию записи. Обновите страницу и повторите действие.",
  [ApiErrorCode.INVALID_WORK_ORDER_STATE]:
    "Действие недоступно в текущем статусе заявки. Данные обновлены.",
  [ApiErrorCode.EQUIPMENT_ARCHIVED]:
    "Оборудование находится в архиве. Для него нельзя создавать заявки и графики ТО.",
  [ApiErrorCode.ACTIVE_WORK_ORDERS]:
    "У оборудования есть незавершённые заявки. Архивирование невозможно.",
  [ApiErrorCode.LAST_ACTIVE_ADMIN]:
    "Нельзя понизить роль или заблокировать последнего активного администратора.",
  [ApiErrorCode.INVALID_DATE_RANGE]:
    "Дата начала периода позже даты окончания.",
  [ApiErrorCode.DUPLICATE_PLANNED_WORK_ORDER]:
    "Для этого срока ТО уже существует заявка.",
  [ApiErrorCode.DUPLICATE_INVENTORY_NUMBER]:
    "Оборудование с таким инвентарным номером уже существует.",
  [ApiErrorCode.DEPENDENCY_UNAVAILABLE]:
    "Сервер временно недоступен. Повторите попытку позже.",
  [ApiErrorCode.ACTIVE_MAINTENANCE_WORK]:
    "По регламенту есть незавершённая плановая заявка. Сначала закройте или отмените её.",
  [ApiErrorCode.TOO_EARLY_TO_COMPLETE]:
    "Слишком рано выполнять плановое ТО: следующий срок не сдвинется вперёд. Выполните работу ближе к сроку.",
  [ApiErrorCode.SAME_ASSIGNEE]: "Заявка уже назначена этому технику.",
  [ApiErrorCode.NOT_ARCHIVED]: "Оборудование не находится в архиве.",
  [ApiErrorCode.ALREADY_ARCHIVED]: "Оборудование уже находится в архиве.",
  [ApiErrorCode.NON_ADVANCING_DUE_DATE]:
    "С новым интервалом следующий срок окажется не позже уже закрытого ТО. Увеличьте интервал.",
  [ApiErrorCode.LOGIN_ALREADY_EXISTS]:
    "Пользователь с таким логином уже существует.",
  [ApiErrorCode.INVALID_ASSIGNEE_ROLE]:
    'Исполнителем может быть только пользователь с ролью "Техник".',
  [ApiErrorCode.INVALID_ASSIGNEE]: "Исполнитель не найден.",
  [ApiErrorCode.ASSIGNEE_NOT_ACTIVE]: "Исполнитель заблокирован.",
  [ApiErrorCode.INCOMPLETE_CHECKLIST]:
    "Отметьте все обязательные пункты чек-листа.",
  [ApiErrorCode.INACTIVE_MAINTENANCE_SCHEDULE]:
    "График ТО неактивен: регламент выключен или оборудование в архиве.",
  [ApiErrorCode.FUTURE_DETECTED_DATE]: "Дата не может быть позже сегодняшней.",
  [ApiErrorCode.FAULT_HAS_ACTIVE_WORK_ORDER]:
    "По этой неисправности уже есть незавершённая заявка.",
  [ApiErrorCode.EQUIPMENT_MISMATCH]:
    "Неисправность или график ТО относятся к другому оборудованию.",
  [ApiErrorCode.DUPLICATE_CHECKLIST_ITEM]:
    "Пункты чек-листа должны иметь уникальные названия и порядковые номера.",
  [ApiErrorCode.DUPLICATE_ACTIVE_WORK_ORDER]:
    "Для этого объекта уже есть незавершённая заявка.",
  [ApiErrorCode.ACTIVE_ASSIGNMENTS]:
    "У техника есть незавершённые заявки. Сначала переназначьте, закройте или отмените их.",
  [ApiErrorCode.MALFORMED_JSON]: TECHNICAL_ERROR_MESSAGE,
  [ApiErrorCode.UNSUPPORTED_MEDIA_TYPE]: TECHNICAL_ERROR_MESSAGE,
  [ApiErrorCode.METHOD_NOT_ALLOWED]: TECHNICAL_ERROR_MESSAGE,
  [ApiErrorCode.NETWORK_ERROR]:
    "Нет связи с сервером. Проверьте подключение к сети.",
};

const FIELD_MESSAGE_RULES: {
  pattern: RegExp;
  build: (match: RegExpMatchArray) => string;
}[] = [
  {
    pattern: /at least (\d+) characters?/i,
    build: (match) => `Минимальная длина: ${match[1]} симв.`,
  },
  {
    pattern: /at most (\d+) characters?/i,
    build: (match) => `Максимальная длина: ${match[1]} симв.`,
  },
  {
    pattern: /greater than or equal to (\d+)/i,
    build: (match) => `Значение должно быть не меньше ${match[1]}.`,
  },
  {
    pattern: /less than or equal to (\d+)/i,
    build: (match) => `Значение должно быть не больше ${match[1]}.`,
  },
  {
    pattern: /valid date/i,
    build: () => "Некорректная дата.",
  },
  {
    pattern: /field required|missing/i,
    build: () => "Обязательное поле.",
  },
  {
    pattern: /should match pattern/i,
    build: () => "Недопустимые символы.",
  },
  {
    pattern: /input should be/i,
    build: () => "Недопустимое значение.",
  },
];

export const translateFieldMessage = (message: string): string => {
  for (const rule of FIELD_MESSAGE_RULES) {
    const match = message.match(rule.pattern);

    if (match) return rule.build(match);
  }

  return "Значение не прошло проверку на сервере.";
};

export const getErrorMessage = (error: unknown): string => {
  if (!isApiError(error)) return DEFAULT_ERROR_MESSAGE;

  if (error.code === ApiErrorCode.RATE_LIMITED && error.retryAfterSeconds) {
    const minutes = Math.ceil(error.retryAfterSeconds / 60);

    return `Слишком много неудачных попыток входа. Повторите через ${minutes} мин.`;
  }

  return ERROR_MESSAGES[error.code] ?? DEFAULT_ERROR_MESSAGE;
};

export const getFieldErrors = (error: unknown): Record<string, string> => {
  if (!isApiError(error)) return {};

  return error.fieldErrors.reduce<Record<string, string>>(
    (result, fieldError) => {
      const fieldName = fieldError.field.split(".")[0];

      if (!result[fieldName])
        result[fieldName] = translateFieldMessage(fieldError.message);

      return result;
    },
    {}
  );
};
