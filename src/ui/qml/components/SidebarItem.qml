import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Button {
    id: root

    property var theme
    property string iconName: ""
    property var iconLibrary
    property bool selected: false

    implicitHeight: 50
    hoverEnabled: true
    Accessible.name: text

    background: Rectangle {
        radius: 10
        color: root.selected ? theme.sidebarActiveItem : (root.hovered ? theme.surfaceBaseHover : "transparent")
        border.width: root.selected ? 1 : 0
        border.color: root.selected ? theme.controlOutline : "transparent"

        Behavior on color { ColorAnimation { duration: 140 } }
        Behavior on border.color { ColorAnimation { duration: 140 } }
    }

    contentItem: RowLayout {
        spacing: 10
        anchors.fill: parent
        anchors.leftMargin: 14
        anchors.rightMargin: 12

        Image {
            source: root.iconLibrary ? root.iconLibrary.svgData(root.iconName, root.selected ? theme.iconStrongBase : theme.iconBase) : ""
            sourceSize.width: 18
            sourceSize.height: 18
            fillMode: Image.PreserveAspectFit
            Layout.preferredWidth: 18
            Layout.preferredHeight: 18
            Accessible.ignored: true
        }

        Text {
            Layout.fillWidth: true
            text: root.text
            color: root.selected ? theme.textStrong : theme.textBase
            font.pixelSize: 14
            font.weight: 500
            elide: Text.ElideRight
        }
    }
}
