import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root

    property var theme
    property string label: ""
    property string description: ""
    property bool checked: false

    signal toggled(bool value)

    implicitHeight: row.implicitHeight

    RowLayout {
        id: row
        anchors.fill: parent
        spacing: 16

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2

            Text {
                text: root.label
                color: theme.textStrong
                font.pixelSize: 13
                font.weight: 500
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }

            Text {
                visible: root.description.length > 0
                text: root.description
                color: theme.textBase
                font.pixelSize: 12
                font.weight: 400
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }
        }

        Switch {
            id: control
            checked: root.checked
            Accessible.name: root.label
            onToggled: root.toggled(checked)

            indicator: Rectangle {
                implicitWidth: 28
                implicitHeight: 16
                radius: 3
                color: control.checked ? theme.iconStrongBase : theme.surfaceBase
                border.width: 1
                border.color: control.checked ? theme.iconStrongBase : theme.borderWeakBase

                Rectangle {
                    width: 14
                    height: 14
                    radius: 2
                    y: 1
                    x: control.checked ? 13 : 1
                    color: theme.iconInvertBase
                    border.width: control.checked ? 0 : 1
                    border.color: theme.borderBase
                }
            }

            contentItem: Item {}
        }
    }
}
