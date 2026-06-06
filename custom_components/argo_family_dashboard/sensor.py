from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ArgoFamilyCoordinator

MAX_SENSOR_ATTRIBUTE_ITEMS = 40


@dataclass(frozen=True, kw_only=True)
class ArgoSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]
    attr_fn: Callable[[dict[str, Any]], dict[str, Any]] = lambda data: {}


SENSORS: tuple[ArgoSensorDescription, ...] = (
    ArgoSensorDescription(
        key="status",
        name="Stato",
        translation_key="status",
        icon="mdi:eye",
        value_fn=lambda data: data.get("status"),
        attr_fn=lambda data: {"updated_at": data.get("updated_at")},
    ),
    ArgoSensorDescription(
        key="last_update",
        name="Ultimo aggiornamento",
        translation_key="last_update",
        icon="mdi:clock-check-outline",
        value_fn=lambda data: data.get("updated_at"),
        attr_fn=lambda data: {
            "updated_at": data.get("updated_at"),
            "status": data.get("status"),
        },
    ),
    ArgoSensorDescription(
        key="student_info",
        name="Info studente",
        translation_key="student_info",
        icon="mdi:account-school",
        value_fn=lambda data: data.get("student_name"),
        attr_fn=lambda data: {
            "nome": data.get("student_name"),
            "codice_scuola": data.get("school_code"),
            "nome_scuola": data.get("school_name"),
            "classe": data.get("class_name"),
            "profilo": data.get("profile", {}),
            "studente": data.get("student", {}),
            "orario": data.get("schedule", [])[:20],
        },
    ),
    ArgoSensorDescription(
        key="average",
        name="Media generale",
        translation_key="average",
        icon="mdi:chart-donut",
        value_fn=lambda data: data.get("average"),
        attr_fn=lambda data: {"subjects": data.get("subjects", [])},
    ),
    ArgoSensorDescription(
        key="subjects",
        name="Materie",
        translation_key="subjects",
        icon="mdi:book-open-variant",
        value_fn=lambda data: len(data.get("subjects", [])),
        attr_fn=lambda data: {"subjects": data.get("subjects", [])},
    ),
    ArgoSensorDescription(
        key="grades",
        name="Voti",
        translation_key="grades",
        icon="mdi:clipboard-list",
        value_fn=lambda data: len(data.get("grades", [])),
        attr_fn=lambda data: {
            "grades": _limit(data.get("grades", [])),
            "totale": len(data.get("grades", [])),
        },
    ),
    ArgoSensorDescription(
        key="latest_grade",
        name="Ultimo voto",
        translation_key="latest_grade",
        icon="mdi:clipboard-text",
        value_fn=lambda data: (data.get("latest_grade") or {}).get("valore") or "Nessun voto",
        attr_fn=lambda data: {
            "latest_grade": data.get("latest_grade"),
            "voti_recenti": data.get("grades", [])[:12],
        },
    ),
    ArgoSensorDescription(
        key="upcoming",
        name="Prossimi impegni",
        translation_key="upcoming",
        icon="mdi:calendar-clock",
        value_fn=lambda data: len(data.get("upcoming", [])),
        attr_fn=lambda data: {"impegni": data.get("upcoming", [])},
    ),
    ArgoSensorDescription(
        key="updates",
        name="Aggiornamenti",
        translation_key="updates",
        icon="mdi:bell-badge",
        value_fn=lambda data: len(data.get("updates", [])),
        attr_fn=lambda data: {
            "aggiornamenti": _limit(data.get("updates", [])),
            "totale": len(data.get("updates", [])),
        },
    ),
    ArgoSensorDescription(
        key="assignments",
        name="Compiti",
        translation_key="assignments",
        icon="mdi:calendar-check",
        value_fn=lambda data: len(data.get("assignments", [])),
        attr_fn=lambda data: {
            "assignments": _limit(data.get("assignments", [])),
            "totale": len(data.get("assignments", [])),
        },
    ),
    ArgoSensorDescription(
        key="pending_assignments",
        name="Compiti da fare",
        translation_key="pending_assignments",
        icon="mdi:calendar-check",
        value_fn=lambda data: len(data.get("pending_assignments", [])),
        attr_fn=lambda data: {"compiti": data.get("pending_assignments", [])},
    ),
    ArgoSensorDescription(
        key="assigned_assignments",
        name="Compiti assegnati",
        translation_key="assigned_assignments",
        icon="mdi:history",
        value_fn=lambda data: len(data.get("assigned_assignments", [])),
        attr_fn=lambda data: {
            "compiti": _limit(data.get("assigned_assignments", [])),
            "totale": len(data.get("assigned_assignments", [])),
        },
    ),
    ArgoSensorDescription(
        key="activities",
        name="Attivita svolte",
        translation_key="activities",
        icon="mdi:clipboard-text-clock",
        value_fn=lambda data: len(data.get("activities", [])),
        attr_fn=lambda data: {
            "attivita": _limit(data.get("activities", [])),
            "totale": len(data.get("activities", [])),
        },
    ),
    ArgoSensorDescription(
        key="register",
        name="Registro",
        translation_key="register",
        icon="mdi:notebook",
        value_fn=lambda data: len(data.get("register", [])),
        attr_fn=lambda data: {
            "register": _limit(data.get("register", [])),
            "totale": len(data.get("register", [])),
        },
    ),
    ArgoSensorDescription(
        key="absences",
        name="Assenze",
        translation_key="absences",
        icon="mdi:account-off",
        value_fn=lambda data: (data.get("attendance") or {}).get("assenze", 0),
        attr_fn=lambda data: data.get("attendance", {}),
    ),
    ArgoSensorDescription(
        key="lessons",
        name="Lezioni",
        translation_key="lessons",
        icon="mdi:teach",
        value_fn=lambda data: len(data.get("lessons", [])),
        attr_fn=lambda data: {
            "lezioni": _limit(data.get("lessons", [])),
            "totale": len(data.get("lessons", [])),
        },
    ),
    ArgoSensorDescription(
        key="memos",
        name="Promemoria",
        translation_key="memos",
        icon="mdi:reminder",
        value_fn=lambda data: len(data.get("memos", [])),
        attr_fn=lambda data: {"promemoria": data.get("memos", [])},
    ),
    ArgoSensorDescription(
        key="communications",
        name="Bacheca",
        translation_key="communications",
        icon="mdi:bulletin-board",
        value_fn=lambda data: len(data.get("communications", [])),
        attr_fn=lambda data: {
            "communications": _limit(data.get("communications", [])),
            "totale": len(data.get("communications", [])),
        },
    ),
    ArgoSensorDescription(
        key="student_communications",
        name="Bacheca alunno",
        translation_key="student_communications",
        icon="mdi:file-document",
        value_fn=lambda data: len(data.get("student_communications", [])),
        attr_fn=lambda data: {"documenti": data.get("student_communications", [])},
    ),
    ArgoSensorDescription(
        key="notes",
        name="Note",
        translation_key="notes",
        icon="mdi:note-text",
        value_fn=lambda data: len(data.get("notes", [])),
        attr_fn=lambda data: {"notes": data.get("notes", [])},
    ),
    ArgoSensorDescription(
        key="schedule",
        name="Orario",
        translation_key="schedule",
        icon="mdi:timetable",
        value_fn=lambda data: len(data.get("schedule", [])),
        attr_fn=lambda data: {"schedule": data.get("schedule", [])},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ArgoFamilyCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [
        ArgoSensor(coordinator, entry, description) for description in SENSORS
    ]
    entities.extend(
        ArgoSubjectSensor(coordinator, entry, subject)
        for subject in (coordinator.data or {}).get("subjects", [])
    )
    async_add_entities(entities)


class ArgoSensor(CoordinatorEntity[ArgoFamilyCoordinator], SensorEntity):
    entity_description: ArgoSensorDescription

    def __init__(
        self,
        coordinator: ArgoFamilyCoordinator,
        entry: ConfigEntry,
        description: ArgoSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        child_name = entry.data.get("child_name") or entry.data.get("name") or "Studente"
        self._attr_name = f"Argo {child_name} {description.name or description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"Argo {child_name}",
            "manufacturer": "Argo",
            "model": "Registro elettronico",
        }

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data or {})

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self.entity_description.attr_fn(self.coordinator.data or {})


class ArgoSubjectSensor(CoordinatorEntity[ArgoFamilyCoordinator], SensorEntity):
    def __init__(
        self,
        coordinator: ArgoFamilyCoordinator,
        entry: ConfigEntry,
        subject: dict[str, Any],
    ) -> None:
        super().__init__(coordinator)
        self._subject_name = str(subject.get("materia") or "Materia")
        self._subject_key = _slugify(self._subject_name)
        child_name = entry.data.get("child_name") or entry.data.get("name") or "Studente"
        self._attr_unique_id = f"{entry.entry_id}_subject_{self._subject_key}"
        self._attr_name = f"Argo {child_name} Materia {self._subject_name}"
        self._attr_icon = "mdi:book-education"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"Argo {child_name}",
            "manufacturer": "Argo",
            "model": "Registro elettronico",
        }

    @property
    def native_value(self) -> Any:
        subject = self._subject()
        if not subject:
            return None
        return subject.get("media")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        subject = self._subject()
        grades = [
            grade
            for grade in (self.coordinator.data or {}).get("grades", [])
            if grade.get("materia") == self._subject_name
        ]
        return {
            "materia": self._subject_name,
            "media": subject.get("media") if subject else None,
            "numero_voti": subject.get("voti") if subject else 0,
            "voti": _limit(grades),
            "totale_voti": len(grades),
        }

    def _subject(self) -> dict[str, Any] | None:
        for subject in (self.coordinator.data or {}).get("subjects", []):
            if str(subject.get("materia")) == self._subject_name:
                return subject
        return None


def _slugify(value: str) -> str:
    result = []
    previous_sep = False
    for char in value.lower():
        if char.isalnum():
            result.append(char)
            previous_sep = False
        elif not previous_sep:
            result.append("_")
            previous_sep = True
    return "".join(result).strip("_")[:48] or "materia"


def _limit(items: Any, limit: int = MAX_SENSOR_ATTRIBUTE_ITEMS) -> Any:
    if isinstance(items, list):
        return items[:limit]
    return items
