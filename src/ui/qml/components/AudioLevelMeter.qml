import QtQuick 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    property var theme
    property real level: 0.0
    property real threshold: 0.02
    property bool active: false
    property bool editable: false

    readonly property real clampedLevel: Math.max(0, Math.min(root.level, 1))
    readonly property real clampedThreshold: Math.max(0, Math.min(root.threshold, 1))

    signal thresholdEdited(real value)

    function updateThresholdFromX(positionX) {
        var width = Math.max(track.width, 1)
        var nextValue = Math.max(0, Math.min(1, positionX / width))
        root.thresholdEdited(nextValue)
    }

    Layout.fillWidth: true
    implicitHeight: meterColumn.implicitHeight

    ColumnLayout {
        id: meterColumn
        anchors.fill: parent
        spacing: 8

        Rectangle {
            id: track
            Layout.fillWidth: true
            implicitHeight: 24
            radius: 12
            color: root.theme.controlSurface
            border.width: 1
            border.color: root.editable ? root.theme.borderHover : (root.active ? root.theme.borderSelected : root.theme.borderWeakBase)
            clip: true

            Rectangle {
                id: levelFill
                width: root.active ? Math.max(6, track.width * root.clampedLevel) : 0
                height: parent.height
                radius: parent.radius
                color: root.active ? root.theme.surfaceBrandBase : root.theme.surfaceRaisedBaseActive

                Behavior on width {
                    NumberAnimation { duration: 110; easing.type: Easing.OutCubic }
                }
            }

            Rectangle {
                id: thresholdLine
                width: 2
                height: parent.height - 8
                radius: 1
                x: Math.max(0, Math.min(track.width - width, track.width * root.clampedThreshold - width / 2))
                y: 4
                color: root.theme.borderSelected
            }

            Rectangle {
                id: thresholdHandle
                visible: root.editable
                width: 12
                height: 12
                radius: 6
                x: Math.max(0, Math.min(track.width - width, track.width * root.clampedThreshold - width / 2))
                y: Math.round((track.height - height) / 2)
                color: root.active ? root.theme.iconStrongBase : root.theme.controlSurface
                border.width: 2
                border.color: root.theme.borderSelected
            }

            MouseArea {
                anchors.fill: parent
                enabled: root.editable
                hoverEnabled: root.editable
                cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor

                onPressed: function(mouse) {
                    root.updateThresholdFromX(mouse.x)
                }

                onPositionChanged: function(mouse) {
                    if (pressed) {
                        root.updateThresholdFromX(mouse.x)
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true

            Text {
                text: root.active ? "Listening to the microphone." : "Meter idle until the mic test starts."
                color: root.theme.textWeak
                font.pixelSize: 13
                font.weight: 400
            }

            Item { Layout.fillWidth: true }

            Text {
                text: "Level " + root.clampedLevel.toFixed(3) + " / Trigger " + root.clampedThreshold.toFixed(3)
                color: root.theme.textWeak
                font.pixelSize: 12
                font.weight: 500
            }
        }

        RowLayout {
            visible: root.editable
            Layout.fillWidth: true

            Text {
                text: "More sensitive"
                color: root.theme.textWeak
                font.pixelSize: 12
                font.weight: 400
            }

            Item { Layout.fillWidth: true }

            Text {
                text: "More selective"
                color: root.theme.textWeak
                font.pixelSize: 12
                font.weight: 400
            }
        }
    }
}
