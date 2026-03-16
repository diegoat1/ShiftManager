import enum


class ShiftStatus(str, enum.Enum):
    DRAFT = "draft"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AssignmentStatus(str, enum.Enum):
    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class AvailabilityType(str, enum.Enum):
    AVAILABLE = "available"
    PREFERRED = "preferred"
    RELUCTANT = "reluctant"


class UnavailabilityReason(str, enum.Enum):
    VACATION = "vacation"
    SICK_LEAVE = "sick_leave"
    PERSONAL = "personal"
    TRAINING = "training"
    OTHER = "other"


class ShiftType(str, enum.Enum):
    DAY = "day"
    NIGHT = "night"
    EVENING = "evening"
    WEEKEND_DAY = "weekend_day"
    WEEKEND_NIGHT = "weekend_night"


class InstitutionType(str, enum.Enum):
    PRONTO_SOCCORSO = "pronto_soccorso"
    PUNTO_PRIMO_INTERVENTO = "punto_primo_intervento"
    GUARDIA_MEDICA = "guardia_medica"
    EMERGENZA_118 = "emergenza_118"
    CASA_DI_COMUNITA = "casa_di_comunita"
    RSA = "rsa"
