from __future__ import annotations

from dataclasses import dataclass

try:
    import sounddevice as sd
except ImportError:  # pragma: no cover - optional runtime dependency.
    sd = None

try:
    from PySide6.QtMultimedia import QMediaDevices
except ImportError:  # pragma: no cover - optional runtime dependency.
    QMediaDevices = None


@dataclass(frozen=True)
class AudioDeviceOption:
    value: str
    label: str


class AudioDeviceService:
    def __init__(
        self,
        *,
        input_devices_provider=None,
        host_apis_provider=None,
        output_devices_provider=None,
        default_output_provider=None,
    ) -> None:
        self._input_devices_provider = (
            input_devices_provider or self._default_input_devices
        )
        self._host_apis_provider = (
            host_apis_provider or self._default_host_apis
        )
        self._has_input_backend = (
            input_devices_provider is not None or sd is not None
        )
        self._output_devices_provider = (
            output_devices_provider or self._default_output_devices
        )
        self._default_output_provider = (
            default_output_provider or self._default_output_device
        )
        self._has_output_backend = (
            output_devices_provider is not None or QMediaDevices is not None
        )

    def list_input_devices(self) -> list[AudioDeviceOption]:
        options = [AudioDeviceOption("default", "System Default Input")]
        if not self._has_input_backend:
            return options
        devices = self._input_devices_provider()
        host_apis = self._host_apis_provider()
        for index, device in enumerate(devices):
            if int(device.get("max_input_channels", 0)) <= 0:
                continue
            options.append(
                AudioDeviceOption(
                    value=f"input:{index}",
                    label=self._device_label(device, host_apis),
                )
            )
        return options

    def list_output_devices(self) -> list[AudioDeviceOption]:
        options = [AudioDeviceOption("default", "System Default Output")]
        if not self._has_output_backend:
            return options
        for device in self._output_devices_provider():
            options.append(
                AudioDeviceOption(
                    value=self._output_value(device),
                    label=device.description() or "Output Device",
                )
            )
        return options

    def resolve_input_device(self, value: str):
        if not value or value == "default":
            return None
        if value.startswith("input:"):
            try:
                return int(value.split(":", 1)[1])
            except ValueError:
                return None
        return value

    def resolve_output_device(self, value: str):
        if not self._has_output_backend:
            return None
        if not value or value == "default":
            return self._default_output_provider()
        for device in self._output_devices_provider():
            if self._output_value(device) == value:
                return device
            if device.description() == value:
                return device
        return self._default_output_provider()

    @staticmethod
    def _device_label(device: dict, host_apis: list[dict]) -> str:
        name = (
            str(device.get("name", "Input Device")).strip() or "Input Device"
        )
        host_api_index = device.get("hostapi")
        host_api_name = ""
        if isinstance(host_api_index, int) and 0 <= host_api_index < len(
            host_apis
        ):
            host_api_name = str(
                host_apis[host_api_index].get("name", "")
            ).strip()
        if host_api_name:
            return f"{name} ({host_api_name})"
        return name

    @staticmethod
    def _output_value(device) -> str:
        return f"output:{bytes(device.id()).hex()}"

    @staticmethod
    def _default_input_devices():
        return sd.query_devices()

    @staticmethod
    def _default_host_apis():
        return sd.query_hostapis()

    @staticmethod
    def _default_output_devices():
        return QMediaDevices.audioOutputs()

    @staticmethod
    def _default_output_device():
        return QMediaDevices.defaultAudioOutput()
