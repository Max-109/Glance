import QtQuick 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    property var theme
    property real level: 0.0
    property real threshold: 0.02
    property bool active: false

    readonly property real clampedLevel: Math.max(0, Math.min(root.level, 1))
    readonly property real clampedThreshold: Math.max(0, Math.min(root.threshold, 1))

    Layout.fillWidth: true
    implicitHeight: meterColumn.implicitHeight

    ColumnLayout {
        id: meterColumn
        anchors.fill: parent
        spacing: 8

        Rectangle {
            id: track
            Layout.fillWidth: true
            implicitHeight: 18
            radius: 9
            color: theme.surfaceBase
            border.width: 1
            border.color: root.active ? theme.borderSelected : theme.borderWeakBase
            clip: true

            Rectangle {
                width: root.active ? Math.max(6, track.width * root.clampedLevel) : 0
                height: parent.height
                radius: parent.radius
                color: root.active ? theme.surfaceBrandBase : theme.surfaceRaisedBaseActive

                Behavior on width {
                    NumberAnimation { duration: 110; easing.type: Easing.OutCubic }
                }
            }

            Rectangle {
                width: 2
                height: parent.height - 4
                radius: 1
                x: Math.max(0, Math.min(track.width - width, track.width * root.clampedThreshold - width / 2))
                y: 2
                color: theme.borderSelected
            }
        }

        RowLayout {
            Layout.fillWidth: true

            Text {
                text: root.active ? "Listening to the microphone." : "Meter idle until the mic test starts."
                color: theme.textWeak
                font.pixelSize: 13
                font.weight: 400
            }

            Item { Layout.fillWidth: true }

            Text {
                text: "Level " + root.clampedLevel.toFixed(3) + " / Trigger " + root.clampedThreshold.toFixed(3)
                color: theme.textWeak
                font.pixelSize: 12
                font.weight: 500
            }
        }
    }
}
